"""Turns a project spec into monthly budget, cost, progress and production data."""
import math
import random
from dataclasses import dataclass, field

from ..config import STATUS_PERIOD
from ..i18n import (CIVIL_ACTIVITIES, COST_TYPE_ORDER, COUNTRIES, COUNTRY_LANG, LANGS,
                    LINEAR_PROGRESS, PIPELINE_ACTIVITIES, activity_name)
from ..services.evm import evm_summary
from ..utils import add_months, first_day, last_day, months_between
from .specs import CO_TEXT, ISSUE_TEXT

UNIT_COST_USD = {"coast": 26_000, "highlands": 41_000, "rainforest": 47_000}  # per inch-km, 2019 base
COUNTRY_FACTOR = {"EC": 1.0, "PE": 0.97, "BR": 1.06}
CO_MARGIN = 0.14
WELDS_PER_KM = 1000 / 12.2


def lower_first(s: str) -> str:
    return s[:1].lower() + s[1:]


def progress_curve(code: str, window: tuple[float, float], x: float) -> float:
    s, e = window
    if x <= s:
        return 0.0
    if x >= e:
        return 1.0
    u = (x - s) / (e - s)
    return u if code in LINEAR_PROGRESS else u * u * (3 - 2 * u)


def fmt_text(triple, params: dict, activity: str) -> tuple[str, str, str]:
    ctx = {f"act_{l}": lower_first(activity_name(activity, l)) for l in LANGS}
    ctx.update({"km": "", "km2": "", "days": "", "rate": "", "n": ""})
    ctx.update(params)
    return tuple(t.format(**ctx) for t in triple)


@dataclass
class SimResult:
    spec: dict
    currency: str
    lang: str
    activities: list  # (code, window, weight, split)
    P: int
    A: int
    n: int
    periods: list
    contract: float
    bid_margin: float
    budget_orig: dict  # a -> ct -> amount
    bac: dict
    planned: dict  # a -> [pct per month]
    actual: dict
    costs: dict  # a -> ct -> [amount per month]
    cos: list
    issues: list
    production: list = field(default_factory=list)
    tasks: list = field(default_factory=list)
    lam: float = 0.0

    @property
    def closed(self) -> bool:
        return self.spec["status"] == "closed"

    @property
    def forecast_finish(self) -> str:
        return add_months(self.spec["start"], self.A - 1)

    @property
    def planned_finish(self) -> str:
        return add_months(self.spec["start"], self.P - 1)


def simulate(spec: dict, fx: dict) -> SimResult:
    rng = random.Random(spec["code"])
    acts = PIPELINE_ACTIVITIES if spec["kind"] == "pipeline" else CIVIL_ACTIVITIES
    currency = COUNTRIES[spec["country"]]["currency"]
    start, P = spec["start"], spec["planned"]
    A = P + spec["delay"]
    closed = spec["status"] == "closed"
    n = A if closed else months_between(start, STATUS_PERIOD) + 1
    if not 0 < n <= A:
        raise ValueError(f"{spec['code']}: status period outside project window")
    periods = [add_months(start, t) for t in range(n)]
    fx_start = fx[(currency, start)]
    year = int(start[:4])

    if spec["kind"] == "pipeline":
        D, L = spec["diameter"], spec["length"]
        usd = (UNIT_COST_USD[spec["terrain"]] * D * L * (L / 40) ** -0.08 * (D / 14) ** -0.1
               * 1.03 ** (year - 2019) * COUNTRY_FACTOR[spec["country"]] * (1 + rng.uniform(-0.05, 0.05)))
    else:
        usd = spec["civil_budget_usd"] * (1 + rng.uniform(-0.03, 0.03))
    budget_total_target = usd / fx_start

    budget_orig = {}
    for code, _, w, split in acts:
        budget_orig[code] = {ct: float(round(budget_total_target * w * s, -2)) for ct, s in zip(COST_TYPE_ORDER, split)}
    budget_total = sum(sum(v.values()) for v in budget_orig.values())
    contract = float(round(budget_total / (1 - spec["bid"]), -3))
    bid_margin = round((contract - budget_total) / contract, 4)
    splits = {code: dict(zip(COST_TYPE_ORDER, split)) for code, _, _, split in acts}

    # Change orders
    cos, lumps = [], {}

    def add_lump(a, idx, amount, mix=None):
        if idx < 0 or idx >= n:
            return
        mix = mix or splits[a]
        for ct, share in mix.items():
            lumps[(a, ct, idx)] = lumps.get((a, ct, idx), 0.0) + amount * share

    bac = {a: sum(v.values()) for a, v in budget_orig.items()}
    approved_rev = 0.0
    for c in spec["cos"]:
        amount = float(round(contract * c["pct"], -2))
        day = 5 + rng.randint(0, 20)
        submitted = f"{c['period']}-{day:02d}"
        decision = None
        if c["status"] in ("approved", "rejected"):
            dd = c.get("decision_days", 45)
            dm = c["period"]
            total_days = day + dd
            while total_days > 28:
                total_days -= 30
                dm = add_months(dm, 1)
            decision = f"{dm}-{max(total_days, 1):02d}"
        texts = c.get("custom") or CO_TEXT[c["cause"]]
        texts = fmt_text(texts, c.get("params", {}), c["activity"])
        co_budget = amount * (1 - CO_MARGIN) if c["status"] == "approved" else 0.0
        co_budget_split = {ct: round(co_budget * s, 2) for ct, s in splits[c["activity"]].items()} if co_budget else {}
        if c["status"] == "approved":
            approved_rev += amount
            bac[c["activity"]] += sum(co_budget_split.values())
        else:
            executed_cost = amount * (1 - 0.12) * c.get("executed", 0.0)
            idx = months_between(start, c["period"])
            span = [i for i in (idx - 2, idx - 1, idx) if 0 <= i < n]
            for i in span:
                add_lump(c["activity"], i, executed_cost / len(span))
        cos.append(dict(
            number=c["number"], cause=c["cause"], activity=c["activity"], amount=amount, status=c["status"],
            submitted_date=submitted, decision_date=decision, period=c["period"],
            schedule_impact_days=rng.choice([0, 0, 10, 15, 20, 30]),
            titles=texts, budget_split=co_budget_split, executed=c.get("executed", 0.0),
        ))

    issues = []
    for period, cat, act, days, cost_pct, params in spec["issues"]:
        amount = float(round(budget_total * cost_pct, -2))
        idx = months_between(start, period)
        add_lump(act, idx, amount, {"EQ": 0.7, "MO": 0.3})
        custom = params.get("custom") if params else None
        p = {k: v for k, v in (params or {}).items() if k != "custom"}
        p["days"] = days
        texts = custom or fmt_text(ISSUE_TEXT[cat], p, act)
        issues.append(dict(period=period, category=cat, activity=act, days=days, cost=amount, texts=texts))

    for period, act, cost_pct in spec.get("unexplained", []):
        add_lump(act, months_between(start, period), float(round(budget_total * cost_pct, -2)), {"EQ": 0.6, "MO": 0.4})

    planned = {code: [progress_curve(code, win, (t + 1) / P) for t in range(n)] for code, win, _, _ in acts}
    actual = {code: [progress_curve(code, win, (t + 1) / A) for t in range(n)] for code, win, _, _ in acts}
    noise = {(code, ct, t): math.exp(rng.gauss(0, 0.07)) for code, *_ in acts for ct in COST_TYPE_ORDER for t in range(A)}
    weights = spec["weights"]

    def run(lam: float) -> dict:
        k = {code: max(0.72, 1 + lam * weights.get(code, 0.0)) for code, *_ in acts}
        costs = {}
        for code, *_ in acts:
            costs[code] = {ct: [0.0] * n for ct in COST_TYPE_ORDER}
            prev = 0.0
            for t in range(n):
                d = actual[code][t] - prev
                prev = actual[code][t]
                for ct in COST_TYPE_ORDER:
                    costs[code][ct][t] = d * bac[code] * k[code] * splits[code][ct] * noise[(code, ct, t)]
        for (a, ct, t), amt in lumps.items():
            costs[a][ct][t] += amt
        return costs

    def margin(costs: dict) -> float:
        ac = {a: sum(sum(v) for v in cts.values()) for a, cts in costs.items()}
        s = evm_summary(bac, ac, {a: actual[a][n - 1] for a in bac}, {a: planned[a][n - 1] for a in bac}, closed)
        revised = contract + approved_rev
        return (revised - s["eac"]) / revised

    lo, hi = -2.0, 8.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if margin(run(mid)) > spec["target"]:
            lo = mid
        else:
            hi = mid
    lam = (lo + hi) / 2
    costs = run(lam)
    for a in costs:
        for ct in costs[a]:
            costs[a][ct] = [float(round(x)) for x in costs[a][ct]]

    sim = SimResult(
        spec=spec, currency=currency, lang=COUNTRY_LANG[spec["country"]], activities=acts,
        P=P, A=A, n=n, periods=periods, contract=contract, bid_margin=bid_margin,
        budget_orig=budget_orig, bac=bac, planned=planned, actual=actual, costs=costs,
        cos=cos, issues=issues, lam=lam,
    )

    if spec["kind"] == "pipeline":
        rep = spec.get("repair", {"base": 0.03})
        welds_prev = repairs = 0
        for t in range(n):
            km = actual["SOL"][t] * spec["length"]
            welds = round(km * WELDS_PER_KM)
            x = (t + 1) / A
            rate = rep["base"]
            if "spike" in rep and rep["spike_from"] <= x <= rep["spike_to"]:
                rate = rep["spike"]
            repairs += round((welds - welds_prev) * rate * math.exp(rng.gauss(0, 0.08)))
            welds_prev = welds
            sim.production.append(dict(period=periods[t], km=round(km, 2), welds=welds, repairs=repairs))

    for uid, (code, (s, e), _, _) in enumerate(acts, start=1):
        bs = add_months(start, int(math.floor(s * P)))
        bf = add_months(start, max(int(math.ceil(e * P)) - 1, int(math.floor(s * P))))
        as_ = add_months(start, int(math.floor(s * A)))
        af = add_months(start, max(int(math.ceil(e * A)) - 1, int(math.floor(s * A))))
        sim.tasks.append(dict(
            uid=uid, activity=code, baseline_start=first_day(bs), baseline_finish=last_day(bf),
            start=first_day(as_), finish=last_day(af), pct=1.0 if closed else round(actual[code][n - 1], 4),
        ))
    return sim
