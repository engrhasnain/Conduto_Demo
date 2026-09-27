"""Earned-value maths shared by the KPI engine and the seed calibration.

EAC per activity uses the CPI method: EAC = AC + (BAC - EV) / CPI, with CPI clamped
to [0.5, 1.5] so one bad month cannot explode a forecast. Below 10% progress the CPI
is not yet meaningful, so the remaining work is forecast at budget instead.
"""

EARLY_PCT = 0.10


def activity_eac(bac: float, ac: float, pct: float, closed: bool) -> float:
    if closed or bac <= 0 or pct >= 0.999:
        return ac
    ev = pct * bac
    if pct < EARLY_PCT:
        return ac + max(bac - ev, 0.0)
    cpi = ev / ac if ac > 0 else 1.0
    cpi = min(max(cpi, 0.5), 1.5)
    return ac + (bac - ev) / cpi


def evm_summary(bac: dict, ac: dict, pct: dict, planned: dict, closed: bool) -> dict:
    per = {}
    default = 1.0 if closed else 0.0
    for a in sorted(set(bac) | set(ac)):
        b = bac.get(a, 0.0)
        c = ac.get(a, 0.0)
        p = pct.get(a, default)
        pl = planned.get(a, default)
        per[a] = {
            "bac": b, "ac": c, "pct": p, "planned": pl,
            "ev": p * b, "pv": pl * b,
            "eac": activity_eac(b, c, p, closed),
            "cpi": (p * b) / c if c > 0 else None,
        }
    tot = {k: sum(v[k] for v in per.values()) for k in ("bac", "ac", "ev", "pv", "eac")}
    tot["cpi"] = tot["ev"] / tot["ac"] if tot["ac"] > 0 else None
    tot["spi"] = tot["ev"] / tot["pv"] if tot["pv"] > 0 else None
    tot["progress"] = tot["ev"] / tot["bac"] if tot["bac"] > 0 else default
    tot["planned"] = tot["pv"] / tot["bac"] if tot["bac"] > 0 else default
    tot["activities"] = per
    return tot
