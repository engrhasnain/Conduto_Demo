"""Synthetic monthly rate series, pesos per dollar, shaped like 2018-2027."""
import math
import random

from ..utils import add_months

# Pesos per dollar. The series only ever goes one way, which is the whole
# reason every figure is also held in dollars: a cost booked in 2019 pesos
# and a cost booked last month are not comparable numbers, and adding them
# up without converting is how a project looks profitable until it is
# closed. The shape is the Argentine peso's, not a smooth curve.
ANNUAL = {
    "ARS": {2018: 28.1, 2019: 48.2, 2020: 70.6, 2021: 95.1, 2022: 130.8,
            2023: 296.2, 2024: 915.0, 2025: 1_180.0, 2026: 1_485.0, 2027: 1_760.0},
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
