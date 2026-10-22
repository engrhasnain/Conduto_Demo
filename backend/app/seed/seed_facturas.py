"""Put the month's supplier invoices through the real pipeline.

Nothing here writes a correct figure straight into the database. Each
invoice is written out as a document, read back by the same reader that
would read a real one, checked by the same checks, and only then saved with
whatever verdict those produced. If the reader gets worse, this screen gets
worse, which is the only honest way to build a demonstration of a reader.

The ones that pass are left **approved and waiting**, not posted. Posting
is what the Bejerman connector does when somebody presses Sync, so that the
meeting can watch it happen rather than be told it already did.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from ..config import SOURCES_DIR
from ..domain import factura as fa
from ..domain.taxid import generate_cuit
from sqlalchemy import select

from ..models import Document, Project, SupplierInvoice
from ..services import invoices as inv
from .facturas import build_facturas

#: The two legal entities. The second one exists so that "billed to the
#: wrong company" is a real exception rather than a hypothetical one.
BUYER_NAME = "Montamar S.A."
BUYER_TAX_ID = generate_cuit(30_712_446)
OTHER_NAME = "Montamar Servicios S.R.L."
OTHER_TAX_ID = generate_cuit(30_598_117)

FACTURA_DIR = "_FACTURAS"


def seed_facturas(db: Session, *, today: dt.date | None = None, count: int = 140) -> dict:
    today = today or dt.date.today()
    out_dir = SOURCES_DIR / FACTURA_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    documents, suppliers = build_facturas(
        buyer_name=BUYER_NAME,
        buyer_tax_id=BUYER_TAX_ID,
        other_name=OTHER_NAME,
        other_tax_id=OTHER_TAX_ID,
        today=today,
        count=count,
    )
    known = {s.tax_id for s in suppliers}

    projects = db.query(Project).order_by(Project.id).all()
    posted_keys: set[tuple[str, int, int]] = set()
    counts = {"read": 0, "approved": 0, "held": 0}

    for position, record in enumerate(documents):
        # The document as it arrived, kept so every figure can be traced
        # back to the page it was read off.
        path = out_dir / record["filename"].replace(".jpg", ".txt").replace(".pdf", ".txt")
        path.write_text(record["text"], encoding="utf-8")

        doc = Document(
            project_id=projects[position % len(projects)].id if projects else None,
            doc_type="supplier_invoice",
            title=record["filename"],
            filename=record["filename"],
            rel_path=f"sources/{FACTURA_DIR}/{path.name}",
            language="es",
            pages=1,
            origin="seed",
        )
        db.add(doc)
        db.flush()

        reading = inv.read(record["text"], record["qr"])
        received = dt.date.fromisoformat(record["received_on"])
        verdict = inv.check(
            reading,
            buyer_tax_id=BUYER_TAX_ID,
            known_tax_ids=known,
            already_posted=posted_keys,
            received_on=received,
        )

        key = (
            "".join(c for c in str(reading.get("vendor_tax_id") or "") if c.isdigit()),
            int(reading.get("point_of_sale") or 0),
            int(reading.get("number") or 0),
        )
        if verdict.ok:
            posted_keys.add(key)

        invoice = SupplierInvoice(
            document_id=doc.id,
            project_id=doc.project_id,
            filename=record["filename"],
            received_on=record["received_on"],
            channel=record["channel"],
            vendor_name=record["supplier_name"],
            vendor_tax_id=str(reading.get("vendor_tax_id") or ""),
            document_type=int(reading.get("document_type") or 0),
            point_of_sale=int(reading.get("point_of_sale") or 0),
            number=int(reading.get("number") or 0),
            invoice_date=reading.get("invoice_date"),
            authorisation_code=str(reading.get("authorisation_code") or ""),
            authorisation_expires=reading.get("authorisation_expires"),
            currency=str(reading.get("currency") or "ARS"),
            net=float(reading.get("net") or 0),
            vat=float(reading.get("vat") or 0),
            perception=float(reading.get("perception") or 0),
            total=float(reading.get("total") or 0),
            status="approved" if verdict.ok else "held",
            exception_kind=verdict.exception_kind,
            exception_detail=verdict.exception_detail,
            checks={"checks": [c.to_dict() for c in verdict.checks], "notes": reading.notes},
            confidence=reading.confidence,
            manual_minutes=record["minutes"],
        )
        # An invoice that passed every check still needed somebody to say
        # so. In the demonstration that is the clerk on duty.
        if verdict.ok:
            invoice.approved_by = "Lucia Ferreyra"
            invoice.approved_at = dt.datetime.utcnow()
            counts["approved"] += 1
        else:
            counts["held"] += 1
        counts["read"] += 1
        db.add(invoice)

    db.flush()

    # Post all but the last handful. Opening the demonstration on
    # "0 posted" reads as broken rather than as ready, and leaving a few
    # approved means pressing Sync in the meeting still does something
    # somebody can watch.
    approved = [
        i for i in db.scalars(
            select(SupplierInvoice).order_by(SupplierInvoice.id)
        ) if i.status == "approved"
    ]
    keep_back = 15
    for invoice in approved[:-keep_back] if len(approved) > keep_back else []:
        inv.post(db, invoice, route="screen")
        counts["posted"] = counts.get("posted", 0) + 1
    db.flush()
    counts["waiting"] = min(keep_back, len(approved))
    return counts
