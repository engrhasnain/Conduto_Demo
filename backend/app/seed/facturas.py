"""Supplier invoices, as documents rather than as rows.

Every invoice here is written out the way a supplier's system prints it and
then read back by the same code that would read a real one. Nothing is
inserted straight into the database with its figures already correct,
because that would demonstrate nothing: the point of the screen this feeds
is that the figures were *read* off a page and *checked* afterwards.

The mix is the mix an accounts payable desk actually sees. Most invoices
are ordinary and should go straight through. A deliberate minority carry
the problems that stop one, in roughly the proportion they turn up:

=====================  ====  ============================================
Planted problem        How   What it proves
                       many
=====================  ====  ============================================
Expired authorisation     4  Not a valid tax document, however neat
Billed to the other       3  Wrong company in the group
  company
Does not add up           3  Transcription error on the page
Unknown supplier          3  Not in the master file; needs opening
Duplicate                 3  Same document arriving twice
Invalid tax number        2  Check digit fails
=====================  ====  ============================================

And three that look like problems and are not, which matter more than the
ones that are, because a system that stops on these is a system somebody
turns off:

* a **Factura B**, whose tax is inside the price;
* a **Factura C** from a small taxpayer, which carries no tax at all;
* an invoice with a **gross-income perception**, where net plus tax does
  not equal the total and the page is still perfectly correct.
"""

from __future__ import annotations

import datetime as dt
import random
from decimal import Decimal

from ..domain import factura as fa
from ..domain.taxid import format_cuit, generate_cuit

SEED = 20_261_022

#: What a cathodic protection contractor buys, and what it costs in pesos.
SUPPLIES: list[tuple[str, str, int]] = [
    ("MM-ANO-MG-17D3", "Anodo de magnesio alto potencial 17 lb con relleno", 96_400),
    ("MM-ANO-MG-32D3", "Anodo de magnesio alto potencial 32 lb con relleno", 168_000),
    ("MM-ANO-ZN-12", "Anodo de zinc tipo galleta 12 kg ASTM B418 tipo II", 121_500),
    ("MM-ANO-MMO-25", "Anodo tubular MMO/titanio 25 mm x 1000 mm", 412_000),
    ("MM-ANO-FESI-45", "Anodo de hierro-silicio-cromo 45 kg", 338_000),
    ("MM-REC-TR-30-20", "Transformador-rectificador 30 V 20 A refrigerado por aire", 2_740_000),
    ("MM-REC-TR-50-40", "Transformador-rectificador 50 V 40 A con telemedicion", 4_880_000),
    ("MM-CAB-HMW-1X10", "Cable HMWPE 1x10 mm2 negro para corriente impresa", 14_900),
    ("MM-CAB-HMW-1X25", "Cable HMWPE 1x25 mm2 negro para corriente impresa", 31_200),
    ("MM-ELE-CUSO4-P", "Electrodo de referencia Cu/CuSO4 portatil", 184_000),
    ("MM-ELE-CUSO4-E", "Electrodo de referencia Cu/CuSO4 enterrado permanente", 268_000),
    ("MM-PMD-TIPO3", "Poste de medicion tipo 3 con bornera de 7 bornes", 227_000),
    ("MM-CAJ-EMP-12", "Caja de empalme 12 bornes IP66 con shunt", 196_000),
    ("MM-JUN-AIS-6", "Junta aislante monobloc 6 pulgadas ANSI 600", 1_960_000),
    ("MM-REV-CINTA-100", "Cinta anticorrosiva de polietileno 100 mm x 30 m", 23_800),
    ("MM-REV-MANGA-200", "Manga termocontraible 200 mm para junta soldada", 74_500),
    ("MM-REL-BENT-25", "Relleno de bentonita y yeso 25 kg", 18_600),
    ("MM-SOL-CAD-15", "Carga de soldadura exotermica cadweld 15 g", 9_400),
    ("MM-PAN-SOL-150", "Panel solar 150 W para rectificador remoto", 615_000),
    ("MM-SRV-CIPS-KM", "Relevamiento CIPS por kilometro de caneria", 142_000),
    ("MM-SRV-DCVG-KM", "Relevamiento DCVG por kilometro de caneria", 158_000),
    ("MM-SRV-RES-PT", "Medicion de resistividad de suelo por punto", 61_000),
]

SUPPLIER_STEMS = [
    "Anodos del Sur", "Proteccion Catodica Austral", "Rectificadores Parana",
    "Cables Industriales Rosario", "Electroquimica del Plata", "Instrumentos Neuquen",
    "Revestimientos Bahia", "Soldaduras Cordoba", "Geotecnia y Suelos Mendoza",
    "Tecnologia Anticorrosiva", "Mediciones y Ensayos del Litoral", "Bentonitas del Norte",
    "Energia Solar Patagonia", "Equipos de Medicion Rosario", "Ferreteria Industrial Avellaneda",
    "Aislaciones Comahue", "Metalurgica San Lorenzo", "Transporte Patagonico",
    "Logistica Comahue", "Fletes del Litoral",
]
SUFFIXES = ["S.A.", "S.R.L.", "S.A.S.", "S.A."]
CITIES = ["Buenos Aires", "Rosario", "Cordoba", "Neuquen", "Bahia Blanca",
          "Mendoza", "Comodoro Rivadavia", "La Plata", "Avellaneda"]

#: How an invoice turned up. A third of them are not files at all.
CHANNELS = (["email"] * 11 + ["scan"] * 5 + ["photo"] * 3 + ["portal"] * 2)

#: Roughly how long one of these takes to type into the accounting system
#: by hand, from the desk's own measurement.
MINUTES_BY_CHANNEL = {"email": 3.5, "portal": 3.0, "scan": 5.5, "photo": 6.5}


class Supplier:
    __slots__ = ("name", "printed_name", "tax_id", "city", "small", "known")

    def __init__(self, index: int, rng: random.Random) -> None:
        stem = SUPPLIER_STEMS[index % len(SUPPLIER_STEMS)]
        self.city = CITIES[index % len(CITIES)]
        suffix = SUFFIXES[index % len(SUFFIXES)]
        self.name = (
            f"{stem} {suffix}" if index < len(SUPPLIER_STEMS)
            else f"{stem} ({self.city}) {suffix}"
        )
        # The name on the paperwork is rarely the name in the master file.
        self.printed_name = (
            self.name.replace(" S.R.L.", " SRL").replace(" S.A.", " SA")
            if index % 3 == 0 else self.name
        )
        # One in nine is a small taxpayer, who issues a Factura C.
        self.small = index % 9 == 4
        self.tax_id = generate_cuit(20_000_000 + index * 53, company=not self.small)
        self.known = True


def _cae(seed: int) -> str:
    return f"{70_000_000_000_000 + (abs(seed) % 9_000_000_000_000):014d}"


def render(
    *,
    supplier: Supplier,
    buyer_name: str,
    buyer_tax_id: str,
    document_type: int,
    point_of_sale: int,
    number: int,
    invoice_date: dt.date,
    order_number: str,
    rows: list[tuple[str, str, int, Decimal]],
    perception_percent: Decimal = Decimal("0"),
    authorisation_code: str = "",
    authorisation_expires: dt.date | None = None,
    currency: str = "ARS",
    total_override: Decimal | None = None,
    spaced: bool = False,
) -> tuple[str, Decimal, Decimal, Decimal, Decimal]:
    """Lay an invoice out the way an Argentine supplier's system prints it."""
    net = fa.money(sum((amount for _, _, _, amount in rows), Decimal("0")))
    if fa.tax_is_separate(document_type):
        rate = fa.DEFAULT_VAT_PERCENT
        vat = fa.money(net * rate / Decimal("100"))
    else:
        rate = Decimal("0")
        vat = Decimal("0")
    perception = fa.money(net * perception_percent / Decimal("100"))
    total = total_override if total_override is not None else fa.money(net + vat + perception)

    gap = "   " if spaced else " "
    gross_income = f"{point_of_sale:03d}-{(number * 7919) % 1000000:06d}-{point_of_sale % 10}"
    body = [
        supplier.printed_name,
        f"CUIT: {format_cuit(supplier.tax_id)}",
        f"Ingresos Brutos: {gross_income}",
        f"{supplier.city}, Argentina",
        "",
        fa.document_type_name(document_type).upper(),
        f"Punto de venta: {point_of_sale:04d}{gap}Comprobante Nro: {number:08d}",
        f"Fecha de emision: {invoice_date.isoformat()}",
        f"Orden de compra: {order_number}",
        f"CUIT del cliente: {format_cuit(buyer_tax_id)}",
        f"Razon social: {buyer_name}",
        f"Moneda: {currency}",
        "",
        "Codigo  Descripcion                                Cant.   P. unitario     Importe",
    ]
    for position, (code, description, quantity, amount) in enumerate(rows, start=1):
        unit = fa.money(amount / quantity)
        body.append(
            f"{position}.{gap}{code} {description}{gap}{quantity}{gap}{unit}{gap}{amount}"
        )
    body += ["", f"Subtotal: {net}"]
    if fa.tax_is_separate(document_type):
        body.append(f"IVA {rate}%: {vat}")
    elif document_type in {fa.FACTURA_B, fa.NOTA_CREDITO_B}:
        body.append("IVA: incluido en el precio")
    else:
        body.append("IVA: no corresponde (responsable monotributo)")
    if perception:
        body.append(f"Percepcion IIBB {perception_percent}%: {perception}")
    body.append(f"Total: {total}")
    if authorisation_code:
        expires = authorisation_expires or invoice_date + dt.timedelta(days=10)
        body += [
            "",
            f"CAE Nro: {authorisation_code}",
            f"Fecha de vencimiento del CAE: {expires.isoformat()}",
        ]
    return "\n".join(body), net, vat, perception, total


def build_facturas(
    *,
    buyer_name: str,
    buyer_tax_id: str,
    other_name: str,
    other_tax_id: str,
    today: dt.date,
    count: int = 140,
    order_numbers: list[str] | None = None,
) -> tuple[list[dict], list[Supplier]]:
    """Write the month's invoices. Returns documents, not rows."""
    rng = random.Random(SEED)
    suppliers = [Supplier(i, rng) for i in range(28)]
    orders = order_numbers or [f"OC-2026-{n:04d}" for n in range(1, 61)]

    # Which positions in the run carry a planted problem. Spread out, so
    # the demonstration does not open on a wall of exceptions.
    problems: dict[int, str] = {}
    for offset, kind in (
        (6, "expired"), (19, "wrong_company"), (27, "does_not_add_up"),
        (33, "unknown_supplier"), (41, "expired"), (48, "duplicate"),
        (55, "bad_tax_id"), (62, "wrong_company"), (70, "does_not_add_up"),
        (77, "unknown_supplier"), (84, "expired"), (91, "duplicate"),
        (98, "bad_tax_id"), (105, "wrong_company"), (112, "does_not_add_up"),
        (119, "unknown_supplier"), (126, "expired"), (133, "duplicate"),
    ):
        if offset < count:
            problems[offset] = kind

    out: list[dict] = []
    issued: list[dict] = []

    for index in range(count):
        problem = problems.get(index, "")
        supplier = suppliers[index % len(suppliers)]
        channel = CHANNELS[index % len(CHANNELS)]
        received = today - dt.timedelta(days=rng.randint(0, 20))
        invoice_date = received - dt.timedelta(days=rng.randint(0, 6))
        point_of_sale = 1 + (index % 7)
        number = 10_000 + index * 13

        if supplier.small:
            document_type = fa.FACTURA_C
        elif index % 11 == 7:
            document_type = fa.FACTURA_B
        else:
            document_type = fa.FACTURA_A

        rows: list[tuple[str, str, int, Decimal]] = []
        for _ in range(rng.randint(1, 4)):
            code, description, price = SUPPLIES[rng.randrange(len(SUPPLIES))]
            quantity = (
                rng.choice([20, 50, 100, 200]) if price < 50_000
                else rng.choice([2, 5, 10, 25]) if price < 500_000
                else rng.choice([1, 1, 2, 3])
            )
            rows.append((code, description, quantity, fa.money(Decimal(price) * quantity)))

        # A perception appears on about one in six, and is correct.
        perception_percent = Decimal("3") if (
            index % 6 == 2 and fa.tax_is_separate(document_type)
        ) else Decimal("0")

        expires = received + dt.timedelta(days=rng.randint(2, 12))
        code_value = _cae(number * 31 + point_of_sale)
        tax_id_printed = supplier.tax_id
        billed_to_name, billed_to_tax = buyer_name, buyer_tax_id
        total_override = None
        known = True

        if problem == "expired":
            expires = received - dt.timedelta(days=rng.randint(3, 25))
        elif problem == "wrong_company":
            billed_to_name, billed_to_tax = other_name, other_tax_id
        elif problem == "bad_tax_id":
            digits = tax_id_printed
            tax_id_printed = digits[:10] + str((int(digits[10]) + 1) % 10)
        elif problem == "unknown_supplier":
            # A supplier nobody has opened an account for yet. The tax
            # number is valid; it is simply not one we know, which is a
            # different problem from a wrong one and needs a different
            # person to fix it.
            known = False
            tax_id_printed = generate_cuit(31_900_000 + index * 7)

        printed = Supplier.__new__(Supplier)
        printed.name = supplier.name
        printed.printed_name = supplier.printed_name
        printed.tax_id = tax_id_printed
        printed.city = supplier.city
        printed.small = supplier.small
        printed.known = known

        text, net, vat, perception, total = render(
            supplier=printed,
            buyer_name=billed_to_name,
            buyer_tax_id=billed_to_tax,
            document_type=document_type,
            point_of_sale=point_of_sale,
            number=number,
            invoice_date=invoice_date,
            order_number=orders[index % len(orders)],
            rows=rows,
            perception_percent=perception_percent,
            authorisation_code=code_value,
            authorisation_expires=expires,
            spaced=channel == "photo",
        )

        if problem == "does_not_add_up":
            # A transcription error on the page: the total is out by a
            # digit. Everything else about the invoice is fine.
            wrong = fa.money(total + Decimal(rng.choice([9000, -9000, 90000])))
            text = text.replace(f"Total: {total}", f"Total: {wrong}")
            total = wrong

        qr = ""
        if channel in {"email", "portal"} and document_type == fa.FACTURA_A and not problem:
            qr = fa.build_qr(
                invoice_date=invoice_date,
                issuer_tax_identifier=tax_id_printed,
                point_of_sale=point_of_sale,
                document_type=document_type,
                number=number,
                total_amount=total,
                receiver_tax_identifier=billed_to_tax,
                authorisation_code=code_value,
            )

        letter = fa.letter_of(document_type)
        record = dict(
            filename=f"F{letter}-{point_of_sale:04d}-{number:08d}.pdf",
            text=text,
            qr=qr,
            channel=channel,
            received_on=received.isoformat(),
            supplier_name=supplier.name,
            supplier_tax_id=supplier.tax_id,
            supplier_known=known,
            minutes=MINUTES_BY_CHANNEL[channel],
            planted=problem,
        )
        out.append(record)
        issued.append(record)

        if problem == "duplicate" and issued:
            # The same document again, under a bare number and as a
            # photograph, which is how a real repeat arrives.
            earlier = issued[max(0, index - 4)]
            out.append(
                dict(
                    filename=f"IMG_{4400 + index}.jpg",
                    text=earlier["text"],
                    qr="",
                    channel="photo",
                    received_on=received.isoformat(),
                    supplier_name=earlier["supplier_name"],
                    supplier_tax_id=earlier["supplier_tax_id"],
                    supplier_known=earlier["supplier_known"],
                    minutes=MINUTES_BY_CHANNEL["photo"],
                    planted="duplicate",
                )
            )

    return out, suppliers
