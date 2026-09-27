import calendar


def add_months(period: str, n: int) -> str:
    y, m = map(int, period.split("-"))
    idx = y * 12 + (m - 1) + n
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


def months_between(a: str, b: str) -> int:
    """Number of months from period a to period b (b - a)."""
    ya, ma = map(int, a.split("-"))
    yb, mb = map(int, b.split("-"))
    return (yb - ya) * 12 + (mb - ma)


def period_range(start: str, end: str) -> list[str]:
    return [add_months(start, i) for i in range(months_between(start, end) + 1)]


def first_day(period: str) -> str:
    return f"{period}-01"


def last_day(period: str) -> str:
    y, m = map(int, period.split("-"))
    return f"{period}-{calendar.monthrange(y, m)[1]:02d}"


def safe_div(a: float, b: float, default: float | None = None) -> float | None:
    return a / b if b else default
