CURRENCY_SYMBOL = {"USD": "USD", "PEN": "S/", "BRL": "R$"}


def fmt_number(x: float, lang: str, decimals: int = 2) -> str:
    s = f"{x:,.{decimals}f}"
    if lang in ("es", "pt"):
        s = s.replace(",", "\0").replace(".", ",").replace("\0", ".")
    return s


def fmt_money(x: float, currency: str, lang: str, decimals: int = 2) -> str:
    return f"{CURRENCY_SYMBOL.get(currency, currency)} {fmt_number(x, lang, decimals)}"


def fmt_date(d: str, lang: str) -> str:
    if not d:
        return ""
    y, m, dd = d.split("-")
    return f"{y}-{m}-{dd}" if lang == "en" else f"{dd}/{m}/{y}"


def fmt_pct(x: float, lang: str, decimals: int = 1) -> str:
    return f"{fmt_number(x * 100, lang, decimals)}%"
