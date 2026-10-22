"""Tax identifier checks.

Argentina's CUIT is eleven digits: a two digit prefix saying what kind of
taxpayer this is, eight digits of identity, and a check digit.

The check digit is a weighted sum modulo eleven, with the weights
5, 4, 3, 2, 7, 6, 5, 4, 3, 2 running left to right across the first ten
digits. Two remainders are special and both are commonly got wrong:

* a remainder of **0** means the check digit is 0, not 11;
* a remainder of **1** means the check digit is 9, and the prefix is issued
  as 23 rather than 20 or 27.

Getting those two wrong rejects a small but steady fraction of perfectly
valid numbers, which is the kind of quiet breakage that puts good invoices
in an exception queue for a month before anybody works out why.

The prefix is checked too, because it carries meaning: 30, 33 and 34 are
companies, and a supplier invoice from a 20 or 27 is a sole trader. That
difference decides which withholdings apply, so reading it off the number
rather than asking is worth doing.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

#: Left to right across the first ten digits.
CUIT_WEIGHTS = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)

#: What the first two digits say about the holder.
CUIT_PREFIXES: dict[str, str] = {
    "20": "persona física (masculino)",
    "23": "persona física (dígito recalculado)",
    "24": "persona física (dígito recalculado)",
    "27": "persona física (femenino)",
    "30": "persona jurídica",
    "33": "persona jurídica",
    "34": "persona jurídica",
    "50": "persona jurídica",
    "51": "persona jurídica",
    "55": "persona jurídica",
}

COMPANY_PREFIXES = {"30", "33", "34", "50", "51", "55"}


@dataclass(slots=True)
class TaxIdentifierCheck:
    identifier: str
    kind: str
    valid: bool
    explanation: str
    rule_applied: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "identifier": self.identifier,
            "kind": self.kind,
            "valid": self.valid,
            "explanation": self.explanation,
            "rule_applied": self.rule_applied,
        }


def format_cuit(number: str) -> str:
    """``30712345674`` becomes ``30-71234567-4``."""
    digits = re.sub(r"\D", "", number or "")
    if len(digits) != 11:
        return (number or "").strip()
    return f"{digits[:2]}-{digits[2:10]}-{digits[10]}"


def cuit_check_digit(first_ten: str) -> int | None:
    digits = re.sub(r"\D", "", first_ten or "")
    if len(digits) != 10:
        return None
    total = sum(int(digits[i]) * CUIT_WEIGHTS[i] for i in range(10))
    remainder = total % 11
    if remainder == 0:
        return 0
    if remainder == 1:
        return 9
    return 11 - remainder


def is_company(number: str) -> bool:
    digits = re.sub(r"\D", "", number or "")
    return len(digits) == 11 and digits[:2] in COMPANY_PREFIXES


def check_cuit(number: str) -> TaxIdentifierCheck:
    """Validate an Argentine CUIT."""
    digits = re.sub(r"\D", "", number or "")
    rule = "suma ponderada 5-4-3-2-7-6-5-4-3-2, módulo 11"

    if len(digits) != 11:
        return TaxIdentifierCheck(
            number or "",
            "cuit",
            False,
            f"Un CUIT tiene once dígitos y este tiene {len(digits)}.",
            rule,
        )

    prefix = digits[:2]
    if prefix not in CUIT_PREFIXES:
        return TaxIdentifierCheck(
            format_cuit(digits),
            "cuit",
            False,
            f"El prefijo {prefix} no corresponde a ningún tipo de contribuyente.",
            rule,
        )

    expected = cuit_check_digit(digits[:10])
    stated = int(digits[10])
    if expected != stated:
        return TaxIdentifierCheck(
            format_cuit(digits),
            "cuit",
            False,
            (
                f"El dígito verificador es {stated} y debería ser {expected}."
            ),
            rule,
        )

    return TaxIdentifierCheck(
        format_cuit(digits),
        "cuit",
        True,
        f"Dígito verificador correcto; {CUIT_PREFIXES[prefix]}.",
        rule,
    )


_EIN_RE = re.compile(r"^\d{2}-?\d{7}$")


def check_employer_identification_number(number: str) -> TaxIdentifierCheck:
    """United States employer identification number: two digits, then seven.

    Kept because some equipment is imported and billed from abroad.
    """
    cleaned = (number or "").strip()
    ok = bool(_EIN_RE.match(cleaned))
    return TaxIdentifierCheck(
        cleaned,
        "united_states_employer_identification_number",
        ok,
        "Nueve dígitos escritos como dos, un guion y siete."
        if ok
        else "No tiene la forma 12-3456789.",
        "sólo verificación de formato; no hay dígito verificador publicado",
    )


def check_tax_identifier(
    number: str, country: str, *, on_date: dt.date | None = None
) -> TaxIdentifierCheck:
    country = (country or "").upper()
    if country in {"AR", ""}:
        return check_cuit(number)
    if country == "US":
        return check_employer_identification_number(number)
    return TaxIdentifierCheck(
        number or "",
        "desconocido",
        True,
        f"No hay verificación definida para {country}; se acepta como viene.",
    )


def generate_cuit(seed: int, *, company: bool = True) -> str:
    """Produce a valid eleven digit CUIT, used only by the demo data loader."""
    prefix = "30" if company else "20"
    body = f"{seed % 100_000_000:08d}"
    check = cuit_check_digit(prefix + body)
    if check is None:  # pragma: no cover - the slice is always ten digits
        check = 0
    return f"{prefix}{body}{check}"


# ---------------------------------------------------------------------------
# Kept under their old names so nothing that imported them breaks.
# ---------------------------------------------------------------------------
def generate_unified_business_number(seed: int, *, on_date: dt.date | None = None) -> str:
    """Deprecated alias. Produces a CUIT."""
    return generate_cuit(seed)
