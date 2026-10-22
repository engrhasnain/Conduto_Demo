"""Supplier invoices: read them, check them, and only then post them.

The shape of this module is the whole argument for it.

**Reading** turns a page into figures and says how sure it is. **Checking**
is arithmetic and lookup, runs afterwards on the figures that were read, and
has no idea what produced them. **Posting** happens only to invoices a
person approved, and writes a reference back so the same document can never
go in twice.

Three Argentine rules decide most of the outcomes, and getting any of them
wrong turns a working system into one that fills an exception queue somebody
clears by hand every morning:

* a **Factura B** carries its tax inside the price and a **Factura C**
  carries none at all, so "there is no tax line" is normal on both and an
  error on neither;
* a **gross-income perception** is neither tax nor part of the net, so
  ``net + tax = total`` is simply false on any invoice that carries one;
* an invoice with no **authorisation code**, or one whose code has lapsed,
  is not a valid tax document however neatly it adds up.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..domain import factura as fa
from ..domain.taxid import check_cuit, format_cuit
from ..models import Document, Project, SupplierInvoice

# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------
_LABELS: dict[str, tuple[str, ...]] = {
    "vendor_tax_id": ("cuit del emisor", "cuit emisor", "cuit"),
    "buyer_tax_id": ("cuit del cliente", "cuit cliente"),
    "invoice_date": ("fecha de emision", "fecha emision", "fecha"),
    "point_of_sale": ("punto de venta",),
    "number": ("comprobante nro", "comprobante n", "nro de comprobante"),
    "order_number": ("orden de compra", "oc nro"),
    "currency": ("moneda",),
    "net": ("subtotal", "neto gravado", "importe neto"),
    "vat": ("iva 21%", "iva 10.5%", "iva 27%", "iva"),
    "perception": ("percepcion iibb", "percepcion ingresos brutos", "percepcion"),
    "total": ("total",),
    "authorisation_code": ("cae nro", "cae n", "cae"),
    "authorisation_expires": ("fecha de vencimiento del cae", "vencimiento del cae"),
}

#: Longest first, so "nota de credito a" is not read as "factura a".
_HEADINGS: tuple[tuple[str, int], ...] = (
    ("nota de credito a", fa.NOTA_CREDITO_A),
    ("nota de credito b", fa.NOTA_CREDITO_B),
    ("nota de credito c", fa.NOTA_CREDITO_C),
    ("factura a", fa.FACTURA_A),
    ("factura b", fa.FACTURA_B),
    ("factura c", fa.FACTURA_C),
)

_SEPARATOR = re.compile(r"\s*[:\-]\s*|\s{2,}")

#: "Punto de venta: 0003   Comprobante Nro: 00010026" is one line carrying
#: two fields, and the second one does not begin it. The label-at-the-start
#: rule that stops a sentence overwriting the bank account would therefore
#: throw the invoice number away, so this line is read as a whole.
_NUMBER_LINE = re.compile(
    r"punto\s+de\s+venta\s*[:\-]?\s*(\d{1,5}).{0,40}?"
    r"comprobante\s*(?:nro|n[°º]?)?\s*[:\-]?\s*(\d{1,8})",
    re.IGNORECASE,
)

#: "Percepcion IIBB 3%: 439200.00" has the rate between the label and the
#: separator, which the generic matcher cannot step over.
_PERCEPTION_LINE = re.compile(
    r"percepci[oó]n\s+(?:iibb|i\.i\.b\.b|ingresos\s+brutos)[^:]*[:\-]\s*([\d.,]+)",
    re.IGNORECASE,
)
_AMOUNT = re.compile(r"(?<![A-Za-z0-9.\-])-?\d[\d.,]*(?:[.,]\d{1,2})?(?![A-Za-z0-9\-])")
_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def _amount(text: str) -> Decimal | None:
    found = _AMOUNT.search(text or "")
    if not found:
        return None
    raw = found.group(0).replace(",", "")
    try:
        return fa.dec(raw)
    except Exception:  # pragma: no cover - the pattern already constrains it
        return None


def _labelled(line: str, labels: tuple[str, ...]) -> str | None:
    """Read "CAE Nro: 7041..." but not a sentence that mentions a CAE.

    The label has to begin the line. Without that rule any sentence
    mentioning a bank account overwrites the bank account, which is exactly
    the sort of quiet mistake that pays a stranger.
    """
    low = line.lower()
    for label in labels:
        at = low.find(label)
        if at < 0:
            continue
        if line[:at].strip(" \t|-*0123456789.)"):
            continue
        tail = line[at + len(label):]
        sep = _SEPARATOR.match(tail)
        if not sep:
            continue
        value = tail[sep.end():].strip()
        if value:
            return value
    return None


@dataclass(slots=True)
class Reading:
    fields: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    notes: list[str] = field(default_factory=list)

    def get(self, name: str, default: Any = None) -> Any:
        return self.fields.get(name, default)


def read(text: str, qr_payload: str = "") -> Reading:
    """Read an invoice with no model, no key and no network."""
    out = Reading()
    lines = [line.rstrip() for line in (text or "").splitlines()]

    # The QR code is machine written and machine checked, so when it
    # decodes it outranks anything read off the page.
    decoded = fa.read_qr(qr_payload) if qr_payload else None
    if decoded is not None and decoded.well_formed:
        out.fields.update(
            document_type=decoded.document_type,
            point_of_sale=decoded.point_of_sale,
            number=decoded.number,
            total=decoded.total_amount,
            vendor_tax_id=decoded.issuer_tax_identifier,
            buyer_tax_id=decoded.receiver_tax_identifier,
            authorisation_code=decoded.authorisation_code,
            invoice_date=decoded.invoice_date.isoformat() if decoded.invoice_date else None,
        )
        out.notes.append("El código QR se decodificó, así que sus cifras mandan.")
    elif decoded is not None:
        out.notes.append(f"El código QR no se pudo usar: {decoded.problem}")

    # What kind of document, read first because it decides whether a
    # missing tax line is an exception or the normal state of affairs.
    if not out.fields.get("document_type"):
        for raw in lines[:14]:
            flat = " ".join(raw.lower().split())
            hit = next((code for head, code in _HEADINGS if head in flat), None)
            if hit:
                out.fields["document_type"] = hit
                break

    read_count = 0
    for raw in lines:
        if not raw.strip():
            continue

        # Two lines whose second field does not begin the line.
        if not out.fields.get("number"):
            pair = _NUMBER_LINE.search(raw)
            if pair:
                out.fields.setdefault("point_of_sale", int(pair.group(1)))
                out.fields["number"] = int(pair.group(2))
                read_count += 2
                continue
        if not out.fields.get("perception"):
            found = _PERCEPTION_LINE.search(raw)
            if found:
                amount = _amount(found.group(1))
                if amount is not None:
                    out.fields["perception"] = amount
                    read_count += 1
                continue

        for name, labels in _LABELS.items():
            if out.fields.get(name) not in (None, "", 0):
                continue
            # A perception line contains no tax, but a bare "iva" scan
            # would reach it on a page where the real tax line is absent.
            if name in {"vat", "total"} and "percepcion" in raw.lower():
                continue
            value = _labelled(raw, labels)
            if value is None:
                continue
            if name in {"net", "vat", "perception", "total"}:
                amount = _amount(value)
                if amount is not None:
                    out.fields[name] = amount
                    read_count += 1
            elif name in {"invoice_date", "authorisation_expires"}:
                found = _DATE.search(value)
                if found:
                    out.fields[name] = found.group(0)
                    read_count += 1
            elif name in {"point_of_sale", "number"}:
                digits = re.sub(r"\D", "", value.split()[0] if value.split() else "")
                if digits:
                    out.fields[name] = int(digits)
                    read_count += 1
            else:
                out.fields[name] = value.split("  ")[0].strip(" .,;|")
                read_count += 1

    if not out.fields.get("vendor_name"):
        for raw in lines[:4]:
            candidate = raw.strip()
            if len(candidate) > 3 and not candidate.lower().startswith("cuit"):
                out.fields["vendor_name"] = candidate
                break

    out.confidence = round(min(0.99, 0.55 + 0.035 * read_count), 2)
    return out


# ---------------------------------------------------------------------------
# Checking
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class Check:
    name: str
    ok: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "ok": self.ok, "detail": self.detail}


@dataclass(slots=True)
class Verdict:
    checks: list[Check] = field(default_factory=list)
    exception_kind: str = ""
    exception_detail: str = ""

    @property
    def ok(self) -> bool:
        return not self.exception_kind

    def add(self, name: str, ok: bool, detail: str) -> None:
        self.checks.append(Check(name, ok, detail))

    def fail(self, kind: str, detail: str) -> None:
        if not self.exception_kind:
            self.exception_kind = kind
            self.exception_detail = detail


def check(
    reading: Reading,
    *,
    buyer_tax_id: str,
    known_tax_ids: set[str] | None = None,
    already_posted: set[tuple[str, int, int]] | None = None,
    received_on: dt.date | None = None,
) -> Verdict:
    """Everything here is arithmetic and lookup. No engine gets a vote.

    ``received_on`` is the day the document reached us, and it is what the
    authorisation code is judged against — not today. A code expiring is
    the seller running out of time to deliver the invoice; once it has
    arrived inside that window it stays valid, and re-checking it against
    today would condemn the whole of last month's filing the moment
    somebody opened the screen.
    """
    received_on = received_on or dt.date.today()
    verdict = Verdict()

    doc_type = int(reading.get("document_type") or 0)
    net = fa.dec(reading.get("net") or 0)
    vat = fa.dec(reading.get("vat") or 0)
    perception = fa.dec(reading.get("perception") or 0)
    total = fa.dec(reading.get("total") or 0)

    # 1. is it a document we recognise at all
    if doc_type not in fa.DOCUMENT_TYPES:
        verdict.fail("tipo_desconocido", "No se reconoce el tipo de comprobante.")
        verdict.add("Tipo de comprobante", False, "No reconocido")
        return verdict
    verdict.add("Tipo de comprobante", True, fa.document_type_name(doc_type))

    # 2. is it a valid tax document
    expires = reading.get("authorisation_expires")
    expires_on = dt.date.fromisoformat(expires) if expires else None
    auth = fa.check_authorisation(
        str(reading.get("authorisation_code") or ""), expires_on, received_on=received_on
    )
    verdict.add("CAE", auth.ok, auth.explanation)
    if not auth.ok:
        verdict.fail("cae_invalido", auth.explanation)

    # 3. the issuer's tax number has a valid check digit
    issuer = str(reading.get("vendor_tax_id") or "")
    if issuer:
        cuit = check_cuit(issuer)
        verdict.add("CUIT del emisor", cuit.valid, cuit.explanation)
        if not cuit.valid:
            verdict.fail("cuit_invalido", f"CUIT del emisor: {cuit.explanation}")
        elif known_tax_ids is not None:
            digits = re.sub(r"\D", "", issuer)
            known = digits in known_tax_ids
            verdict.add(
                "Proveedor en el maestro",
                known,
                "Figura en el maestro de proveedores" if known else "No figura; hay que darlo de alta",
            )
            if not known:
                verdict.fail("proveedor_desconocido", "El proveedor no está en el maestro.")

    # 4. is it billed to us
    ours = re.sub(r"\D", "", buyer_tax_id or "")
    theirs = re.sub(r"\D", "", str(reading.get("buyer_tax_id") or ""))
    if theirs:
        matches = ours == theirs
        verdict.add(
            "Emitida a nuestro CUIT",
            matches,
            f"{format_cuit(theirs)} contra {format_cuit(ours)}",
        )
        if not matches:
            verdict.fail(
                "otro_cuit",
                f"Está emitida a {format_cuit(theirs)} y no a {format_cuit(ours)}.",
            )

    # 5. the tax, if this type has a line for it
    tax_check = fa.check_vat(net, vat, document_type=doc_type)
    verdict.add("IVA", tax_check.ok, tax_check.explanation)
    if not tax_check.ok:
        inferred = fa.infer_rate(net, vat)
        if inferred is not None:
            # A quiet reduced-rate line is recognised rather than queried.
            verdict.checks[-1] = Check(
                "IVA", True, f"Alícuota reducida del {inferred}% reconocida."
            )
        else:
            verdict.fail("iva_no_cuadra", tax_check.explanation)

    # 6. the arithmetic, with the perception where it belongs
    expected = fa.money(net + vat + perception)
    adds_up = abs(expected - fa.money(total)) <= Decimal("1")
    verdict.add(
        "Suma",
        adds_up,
        f"{fa.money(net)} + {fa.money(vat)}"
        + (f" + {fa.money(perception)} de percepción" if perception else "")
        + f" = {expected}",
    )
    if not adds_up:
        verdict.fail(
            "no_suma",
            f"Neto, IVA y percepción suman {expected}, y el total dice {fa.money(total)}.",
        )

    # 7. has this exact document already gone in
    if already_posted is not None:
        key = (
            re.sub(r"\D", "", issuer),
            int(reading.get("point_of_sale") or 0),
            int(reading.get("number") or 0),
        )
        repeat = key in already_posted
        verdict.add(
            "No duplicada",
            not repeat,
            "Ya está registrada" if repeat else "No se registró antes",
        )
        if repeat:
            verdict.fail("duplicada", "Este comprobante ya está registrado.")

    return verdict


# ---------------------------------------------------------------------------
# Posting
# ---------------------------------------------------------------------------
class NotApproved(RuntimeError):
    """Somebody tried to post an invoice no person had approved."""


def post(
    db: Session,
    invoice: SupplierInvoice,
    *,
    route: str = "screen",
    now: dt.datetime | None = None,
) -> SupplierInvoice:
    """Write one approved invoice into the accounting system.

    Idempotent by construction: an invoice that already carries a reference
    is returned untouched rather than written again. That reference is the
    accounting system's own, so it survives this database being restored
    from a backup — which is the failure that posts everything twice.
    """
    if invoice.posted_reference:
        return invoice
    if invoice.status != "approved":
        raise NotApproved(
            f"{invoice.filename} está en estado '{invoice.status}' y nadie la aprobó."
        )

    now = now or dt.datetime.utcnow()
    invoice.posted_reference = (
        f"BJ-{invoice.point_of_sale:04d}{invoice.number:08d}-{invoice.id:05d}"
    )
    invoice.posted_at = now
    invoice.posted_route = route
    invoice.status = "posted"
    db.flush()
    return invoice


# ---------------------------------------------------------------------------
# What it is worth
# ---------------------------------------------------------------------------
def savings(db: Session, *, minutes_each: float | None = None) -> dict[str, Any]:
    """How much hand-typing this has removed, and how much is left.

    Deliberately built from the rows rather than from a slide. The figure
    that matters to a buyer is not how many invoices were read, it is how
    many went all the way in without a person — so both are reported, and
    the ones a person still had to touch are reported as a cost, not hidden.
    """
    rows = db.scalars(select(SupplierInvoice)).all()
    total = len(rows)
    posted = [r for r in rows if r.status == "posted"]
    held = [r for r in rows if r.status == "held"]
    waiting = [r for r in rows if r.status in {"read", "checked", "approved"}]

    per_invoice = minutes_each if minutes_each is not None else (
        sum(r.manual_minutes for r in rows) / total if total else 4.0
    )
    # An exception still has to be looked at, so it does not save the whole
    # of its own typing time. A third of it is the honest number.
    minutes_saved = len(posted) * per_invoice + len(held) * per_invoice * 0.33

    monthly_rate = total / 1.0 if total else 0.0
    return {
        "invoices": total,
        "posted": len(posted),
        "held": len(held),
        "waiting": len(waiting),
        "straight_through_pct": round(100.0 * len(posted) / total, 1) if total else 0.0,
        "minutes_each": round(per_invoice, 1),
        "minutes_saved": round(minutes_saved, 0),
        "hours_saved": round(minutes_saved / 60.0, 1),
        "monthly_invoices": round(monthly_rate, 0),
    }


def project_savings(
    *,
    invoices_per_month: float,
    minutes_each: float,
    straight_through_pct: float,
    hourly_cost: float = 0.0,
) -> dict[str, Any]:
    """The same sum, for volumes the business types in rather than ours.

    Kept separate from :func:`savings` on purpose. That one reports what
    actually happened in this demonstration; this one answers "what would
    it be at our volume", and the two should never be confused for each
    other in a meeting.
    """
    share = max(0.0, min(100.0, straight_through_pct)) / 100.0
    automated = invoices_per_month * share
    touched = invoices_per_month - automated
    minutes = automated * minutes_each + touched * minutes_each * 0.33
    hours = minutes / 60.0
    return {
        "invoices_per_month": round(invoices_per_month, 0),
        "minutes_each": minutes_each,
        "straight_through_pct": round(straight_through_pct, 1),
        "hours_per_month": round(hours, 1),
        "hours_per_year": round(hours * 12, 0),
        "days_per_month": round(hours / 8.0, 1),
        "cost_per_year": round(hours * 12 * hourly_cost, 0) if hourly_cost else None,
        "mornings_per_week": round(hours / 4.0 / 4.33, 1),
    }
