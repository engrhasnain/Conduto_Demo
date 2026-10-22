"""Argentine electronic invoices (facturas electrónicas).

Four things matter to accounts payable, and all four are checkable without
reading a word of the page:

* the **type** — A, B or C — decides whether tax is shown separately at all,
  which is the trap: an extractor that assumes it always is reads a Factura B
  as having no tax, and a Factura C as being short by twenty-one per cent;
* the **number** is a point of sale and a sequence, ``0003-00001234``;
* the **CAE** is the authorisation code the tax authority issued, fourteen
  digits, with its own expiry date — an invoice with no CAE, or one whose CAE
  has lapsed, is not a valid tax document and must not be posted;
* the **QR code** (General Resolution 4892/2020) carries the issuer, the
  amount, the type, the number and the CAE as base64 JSON, so it can be
  cross-checked against whatever was read off the page.

The QR code is the same idea as any machine-written stamp on a document: it
was produced by the issuing system and checked by the tax authority, so when
it decodes it outranks the printed page. That is the one place this product
lets a document overrule its own reading, and the reason is that the page can
be a photograph of a crooked sheet of paper while the code cannot.

What each type means for the arithmetic:

=========  ====================================  ==========================
Type       Issued by, to                          Tax on the face
=========  ====================================  ==========================
A          Registered business → registered       Shown separately. Net +
           business                               tax = total.
B          Registered business → final consumer   Included in the price. No
           or small-taxpayer                      separate line to check.
C          Small taxpayer (monotributista) →      None. There is no tax to
           anybody                                find, and none is owed.
=========  ====================================  ==========================
"""

from __future__ import annotations

import base64
import binascii
import datetime as dt
import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP



def dec(value) -> Decimal:
    """Anything number-shaped, as an exact Decimal."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value).replace(",", "").strip() or "0")


def money(value) -> Decimal:
    """Two places, half up, the way an invoice is printed."""
    return dec(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Document types
# ---------------------------------------------------------------------------
#: The authority's numeric codes for the document types this business sees.
FACTURA_A = 1
NOTA_DEBITO_A = 2
NOTA_CREDITO_A = 3
FACTURA_B = 6
NOTA_DEBITO_B = 7
NOTA_CREDITO_B = 8
FACTURA_C = 11
NOTA_DEBITO_C = 12
NOTA_CREDITO_C = 13

DOCUMENT_TYPES: dict[int, str] = {
    FACTURA_A: "Factura A",
    NOTA_DEBITO_A: "Nota de débito A",
    NOTA_CREDITO_A: "Nota de crédito A",
    FACTURA_B: "Factura B",
    NOTA_DEBITO_B: "Nota de débito B",
    NOTA_CREDITO_B: "Nota de crédito B",
    FACTURA_C: "Factura C",
    NOTA_DEBITO_C: "Nota de débito C",
    NOTA_CREDITO_C: "Nota de crédito C",
}

#: Types where tax is shown as its own line and can therefore be checked.
TAX_IS_SEPARATE = {FACTURA_A, NOTA_DEBITO_A, NOTA_CREDITO_A}

#: Types that reduce what is owed rather than increase it.
CREDIT_TYPES = {NOTA_CREDITO_A, NOTA_CREDITO_B, NOTA_CREDITO_C}


def document_type_name(code: int) -> str:
    return DOCUMENT_TYPES.get(code, f"Comprobante tipo {code}")


def letter_of(code: int) -> str:
    name = DOCUMENT_TYPES.get(code, "")
    return name[-1] if name else "?"


def tax_is_separate(code: int) -> bool:
    """Is there a tax line on the face of this document to check?

    The question the whole extractor hangs off. A Factura B states one
    number, tax included; a Factura C states one number with no tax in it
    at all. Checking either against a twenty-one per cent rule produces a
    confident, wrong exception on a perfectly good invoice.
    """
    return code in TAX_IS_SEPARATE


# ---------------------------------------------------------------------------
# Tax rates
# ---------------------------------------------------------------------------
#: The general rate. A setting rather than a constant, because a rate written
#: into code is a rate nobody can change.
DEFAULT_VAT_PERCENT = Decimal("21")

#: The reduced rate, which applies to some of what this business buys.
REDUCED_VAT_PERCENT = Decimal("10.5")

VALID_VAT_PERCENTS = (
    Decimal("0"),
    Decimal("2.5"),
    Decimal("5"),
    REDUCED_VAT_PERCENT,
    DEFAULT_VAT_PERCENT,
    Decimal("27"),
)


# ---------------------------------------------------------------------------
# The number
# ---------------------------------------------------------------------------
#: Point of sale, then sequence. Written with or without the dash, and
#: sometimes with the type letter in front of it.
FACTURA_NUMBER = re.compile(
    r"^(?:[ABC]\s*)?(\d{1,5})\s*[-–—]?\s*(\d{1,8})$", re.IGNORECASE
)


def is_factura_number(value: str) -> bool:
    return bool(FACTURA_NUMBER.match((value or "").strip()))


def normalise_factura_number(value: str) -> str:
    """``3-1234``, ``0003 00001234`` and ``A 0003-00001234`` all agree."""
    match = FACTURA_NUMBER.match((value or "").strip())
    if not match:
        return (value or "").strip()
    return f"{int(match.group(1)):04d}-{int(match.group(2)):08d}"


def split_factura_number(value: str) -> tuple[int, int] | None:
    match = FACTURA_NUMBER.match((value or "").strip())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


# ---------------------------------------------------------------------------
# The authorisation code
# ---------------------------------------------------------------------------
CAE = re.compile(r"^\d{14}$")


def is_cae(value: str) -> bool:
    return bool(CAE.match(re.sub(r"\s", "", value or "")))


@dataclass(slots=True)
class AuthorisationCheck:
    """Is this a valid tax document at all?

    Separate from the arithmetic on purpose. An invoice can add up perfectly
    and still not be something the business may deduct tax on, and that is a
    refusal rather than a query.
    """

    ok: bool
    code: str
    expires_on: dt.date | None
    explanation: str

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "code": self.code,
            "expires_on": self.expires_on.isoformat() if self.expires_on else "",
            "explanation": self.explanation,
        }


def check_authorisation(
    code: str,
    expires_on: dt.date | None,
    *,
    received_on: dt.date | None = None,
) -> AuthorisationCheck:
    cleaned = re.sub(r"\s", "", code or "")
    received_on = received_on or dt.date.today()

    if not cleaned:
        return AuthorisationCheck(
            ok=False,
            code="",
            expires_on=expires_on,
            explanation=(
                "No tiene CAE. Sin código de autorización no es un comprobante "
                "válido y no puede registrarse."
            ),
        )
    if not is_cae(cleaned):
        return AuthorisationCheck(
            ok=False,
            code=cleaned,
            expires_on=expires_on,
            explanation=(
                f"El CAE tiene {len(cleaned)} dígitos y debe tener 14."
            ),
        )
    if expires_on is not None and received_on > expires_on:
        days = (received_on - expires_on).days
        return AuthorisationCheck(
            ok=False,
            code=cleaned,
            expires_on=expires_on,
            explanation=(
                f"El CAE venció el {expires_on.isoformat()}, hace {days} días."
            ),
        )
    return AuthorisationCheck(
        ok=True,
        code=cleaned,
        expires_on=expires_on,
        explanation="CAE válido.",
    )


# ---------------------------------------------------------------------------
# The QR code
# ---------------------------------------------------------------------------
QR_PREFIX = "https://www.afip.gob.ar/fe/qr/?p="


@dataclass(slots=True)
class QrPayload:
    """What the printed QR code says, decoded."""

    version: int = 1
    invoice_date: dt.date | None = None
    issuer_tax_identifier: str = ""
    point_of_sale: int = 0
    document_type: int = 0
    number: int = 0
    total_amount: Decimal = Decimal("0")
    currency: str = "PES"
    rate: Decimal = Decimal("1")
    receiver_tax_identifier: str = ""
    authorisation_kind: str = ""
    authorisation_code: str = ""
    well_formed: bool = True
    problem: str = ""

    @property
    def invoice_number(self) -> str:
        return f"{self.point_of_sale:04d}-{self.number:08d}"

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "invoice_date": self.invoice_date.isoformat() if self.invoice_date else "",
            "issuer_tax_identifier": self.issuer_tax_identifier,
            "point_of_sale": self.point_of_sale,
            "document_type": self.document_type,
            "document_type_name": document_type_name(self.document_type),
            "number": self.number,
            "invoice_number": self.invoice_number,
            "total_amount": str(self.total_amount),
            "currency": self.currency,
            "rate": str(self.rate),
            "receiver_tax_identifier": self.receiver_tax_identifier,
            "authorisation_kind": self.authorisation_kind,
            "authorisation_code": self.authorisation_code,
            "well_formed": self.well_formed,
            "problem": self.problem,
        }


def build_qr(
    *,
    invoice_date: dt.date,
    issuer_tax_identifier: str,
    point_of_sale: int,
    document_type: int,
    number: int,
    total_amount: Decimal,
    receiver_tax_identifier: str,
    authorisation_code: str,
    currency: str = "PES",
    rate: Decimal = Decimal("1"),
) -> str:
    """Produce a payload in the published layout, used by the data generator."""
    body = {
        "ver": 1,
        "fecha": invoice_date.isoformat(),
        "cuit": int(re.sub(r"\D", "", issuer_tax_identifier) or 0),
        "ptoVta": point_of_sale,
        "tipoCmp": document_type,
        "nroCmp": number,
        "importe": float(dec(total_amount)),
        "moneda": currency,
        "ctz": float(dec(rate)),
        "tipoDocRec": 80,
        "nroDocRec": int(re.sub(r"\D", "", receiver_tax_identifier) or 0),
        "tipoCodAut": "E",
        "codAut": int(re.sub(r"\D", "", authorisation_code) or 0),
    }
    encoded = base64.b64encode(
        json.dumps(body, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return f"{QR_PREFIX}{encoded}"


def read_qr(payload: str) -> QrPayload | None:
    """Decode the payload. Returns None when there is nothing to decode."""
    raw = (payload or "").strip()
    if not raw:
        return None

    encoded = raw[len(QR_PREFIX):] if raw.startswith(QR_PREFIX) else raw
    encoded = encoded.strip()
    # A photographed code sometimes loses its padding.
    encoded += "=" * (-len(encoded) % 4)

    try:
        decoded = base64.b64decode(encoded, validate=False)
        body = json.loads(decoded.decode("utf-8"))
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return QrPayload(
            well_formed=False,
            problem="El código QR no se puede decodificar.",
        )
    if not isinstance(body, dict):
        return QrPayload(
            well_formed=False, problem="El código QR no contiene un comprobante."
        )

    def as_date(value: object) -> dt.date | None:
        try:
            return dt.date.fromisoformat(str(value))
        except (TypeError, ValueError):
            return None

    def as_decimal(value: object) -> Decimal:
        try:
            return dec(str(value))
        except (TypeError, ValueError, ArithmeticError):
            return Decimal("-1")

    def as_int(value: object) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    out = QrPayload(
        version=as_int(body.get("ver", 1)),
        invoice_date=as_date(body.get("fecha")),
        issuer_tax_identifier=str(body.get("cuit", "")),
        point_of_sale=as_int(body.get("ptoVta")),
        document_type=as_int(body.get("tipoCmp")),
        number=as_int(body.get("nroCmp")),
        total_amount=as_decimal(body.get("importe", 0)),
        currency=str(body.get("moneda", "PES")),
        rate=as_decimal(body.get("ctz", 1)),
        receiver_tax_identifier=str(body.get("nroDocRec", "")),
        authorisation_kind=str(body.get("tipoCodAut", "")),
        authorisation_code=str(body.get("codAut", "")),
    )
    if out.total_amount < 0:
        out.well_formed = False
        out.problem = "El importe del código QR no es legible."
    elif out.invoice_date is None:
        out.well_formed = False
        out.problem = "La fecha del código QR no es una fecha real."
    elif out.document_type not in DOCUMENT_TYPES:
        out.well_formed = False
        out.problem = f"El tipo de comprobante {out.document_type} no se reconoce."
    return out


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class TaxCheck:
    ok: bool
    expected_tax: Decimal
    stated_tax: Decimal
    difference: Decimal
    rate_percent: Decimal = DEFAULT_VAT_PERCENT
    #: True when the document type carries no separate tax line, so there
    #: was nothing to check and nothing is wrong.
    not_applicable: bool = False
    explanation: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "expected_tax": str(self.expected_tax),
            "stated_tax": str(self.stated_tax),
            "difference": str(self.difference),
            "rate_percent": str(self.rate_percent),
            "not_applicable": self.not_applicable,
            "explanation": self.explanation,
        }


def check_vat(
    net: Decimal,
    stated_tax: Decimal,
    *,
    document_type: int = FACTURA_A,
    rate_percent: Decimal = DEFAULT_VAT_PERCENT,
    tolerance: Decimal = Decimal("1"),
) -> TaxCheck:
    """Does the stated tax match the net at the stated rate?

    A Factura B or C has no separate tax line, so there is nothing to check
    and the answer is *not applicable* rather than *wrong*. Returning a
    failure here is how a correct invoice ends up in an exception queue.
    """
    if not tax_is_separate(document_type):
        return TaxCheck(
            ok=True,
            expected_tax=Decimal("0"),
            stated_tax=dec(stated_tax),
            difference=Decimal("0"),
            rate_percent=Decimal("0"),
            not_applicable=True,
            explanation=(
                f"{document_type_name(document_type)} no discrimina IVA; "
                "no hay línea de impuesto para verificar."
            ),
        )

    expected = money(dec(net) * dec(rate_percent) / Decimal("100"))
    stated = money(stated_tax)
    difference = money(stated - expected)
    ok = abs(difference) <= tolerance
    return TaxCheck(
        ok=ok,
        expected_tax=expected,
        stated_tax=stated,
        difference=difference,
        rate_percent=dec(rate_percent),
        explanation=(
            f"{money(net)} al {rate_percent}% = {expected}"
            + ("" if ok else f", pero el comprobante dice {stated}")
        ),
    )


def infer_rate(net: Decimal, stated_tax: Decimal) -> Decimal | None:
    """Which published rate, if any, explains this pair?

    Used when the page states a tax figure that fails at the general rate.
    Some of what this business buys carries the reduced rate, and a quiet
    reduced-rate line should be recognised rather than queried.
    """
    base = dec(net)
    if base <= 0:
        return None
    for candidate in VALID_VAT_PERCENTS:
        expected = money(base * candidate / Decimal("100"))
        if abs(money(stated_tax) - expected) <= Decimal("1"):
            return candidate
    return None
