"""Synthetic monthly FX series (local currency per USD), shaped like 2018-2027 history."""
import math
import random

from ..utils import add_months

ANNUAL = {
    "PEN": {2018: 3.29, 2019: 3.34, 2020: 3.50, 2021: 3.88, 2022: 3.84, 2023: 3.74, 2024: 3.76, 2025: 3.70, 2026: 3.62, 2027: 3.60},
    "BRL": {2018: 3.65, 2019: 3.95, 2020: 5.16, 2021: 5.40, 2022: 5.16, 2023: 4.99, 2024: 5.39, 2025: 5.60, 2026: 5.45, 2027: 5.40},
}

FIRST, LAST = "2018-01", "2027-12"


def build_fx() -> dict[tuple[str, str], float]:
    """Returns {(currency, period): usd_per_unit}."""
    rng = random.Random(42)
    out = {}
    p = FIRST
    while p <= LAST:
        y, m = int(p[:4]), int(p[5:])
        out[("USD", p)] = 1.0
        for cur, table in ANNUAL.items():
            # interpolate between mid-year anchors
            x = y + (m - 0.5) / 12 - 0.5
            y0 = min(max(int(math.floor(x)), 2018), 2026)
            frac = min(max(x - y0, 0.0), 1.0)
            local = table[y0] * (1 - frac) + table[y0 + 1] * frac
            local *= 1 + rng.gauss(0, 0.008)
            out[(cur, p)] = round(1 / local, 6)
        p = add_months(p, 1)
    return out
