"""Parsing helpers for values found in real-world spreadsheets and documents."""
import re
import unicodedata
from datetime import date, datetime

MONTH_TOKENS = {
    "ene": 1, "enero": 1, "jan": 1, "january": 1, "janeiro": 1,
    "feb": 2, "febrero": 2, "fev": 2, "fevereiro": 2, "february": 2,
    "mar": 3, "marzo": 3, "marco": 3, "march": 3,
    "abr": 4, "abril": 4, "apr": 4, "april": 4,
    "may": 5, "mayo": 5, "mai": 5, "maio": 5,
    "jun": 6, "junio": 6, "junho": 6, "june": 6,
    "jul": 7, "julio": 7, "julho": 7, "july": 7,
    "ago": 8, "agosto": 8, "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "set": 9, "septiembre": 9, "setiembre": 9, "setembro": 9, "september": 9,
    "oct": 10, "octubre": 10, "out": 10, "outubro": 10, "october": 10,
    "nov": 11, "noviembre": 11, "novembro": 11, "november": 11,
    "dic": 12, "diciembre": 12, "dez": 12, "dezembro": 12, "dec": 12, "december": 12,
}


def strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))


def norm(s) -> str:
    if s is None:
        return ""
    s = strip_accents(str(s)).lower()
    s = re.sub(r"[^a-z0-9%]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_period(v) -> str | None:
    if isinstance(v, (datetime, date)):
        return f"{v.year:04d}-{v.month:02d}"
    if v is None or isinstance(v, (int, float)):
        return None
    s = strip_accents(str(v)).strip().lower()
    if not s or len(s) > 20:
        return None
    m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})(?:[-/.]\d{1,2})?", s)
    if m and 1 <= int(m.group(2)) <= 12:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"
    m = re.fullmatch(r"(\d{1,2})[-/.](\d{4})", s)
    if m and 1 <= int(m.group(1)) <= 12:
        return f"{int(m.group(2)):04d}-{int(m.group(1)):02d}"
    m = re.fullmatch(r"([a-z]+)\.?[\s\-/.]*(?:de\s+)?(\d{2}|\d{4})", s)
    if m and m.group(1) in MONTH_TOKENS:
        y = int(m.group(2))
        y = y + 2000 if y < 100 else y
        return f"{y:04d}-{MONTH_TOKENS[m.group(1)]:02d}"
    return None


def parse_number(v) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s or s in {"-", "–", "—"}:
        return None
    neg = (s.startswith("(") and s.endswith(")")) or s.startswith("-")
    s = re.sub(r"[^\d,.]", "", s)
    if not re.search(r"\d", s):
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3 and parts[0] not in ("", "0")):
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
    elif "." in s:
        parts = s.split(".")
        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3 and parts[0] not in ("", "0")):
            s = s.replace(".", "")
    try:
        x = float(s)
    except ValueError:
        return None
    return -x if neg else x
