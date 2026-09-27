"""Historical benchmarks from closed pipeline projects, and a bid estimator built on them.

Costs are converted to USD at the FX of each project's finish month and escalated
to 2026 at 3%/year so projects from different years are comparable."""
from collections import defaultdict
from datetime import date
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..i18n import PIPELINE_ACTIVITIES
from ..models import BudgetLine, CostActual, Project, ProjectKpi, ScheduleTask
from ..utils import months_between
from .kpis import fx_for, fx_table

ESCALATION = 0.03
BASE_YEAR = 2026


def _pct(values: list[float], q: float) -> float:
    v = sorted(values)
    if not v:
        return 0.0
    i = (len(v) - 1) * q
    lo, hi = int(i), min(int(i) + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (i - lo)


def scale_factor(length_km: float, diameter_in: float) -> float:
    return (length_km / 40) ** -0.08 * (diameter_in / 14) ** -0.1


def closed_pipelines(db: Session) -> list[dict]:
    fx = fx_table(db)
    rows = db.execute(select(Project, ProjectKpi).join(ProjectKpi, ProjectKpi.project_id == Project.id)
                      .where(Project.status == "closed", Project.kind == "pipeline")).all()
    out = []
    for p, k in rows:
        finish = k.as_of_period
        rate = fx_for(fx, p.currency, finish)
        esc = (1 + ESCALATION) ** (BASE_YEAR - int(finish[:4]))
        cost_usd = k.eac * rate * esc
        orig = sum(b.amount for b in db.scalars(select(BudgetLine).where(BudgetLine.project_id == p.id, BudgetLine.origin == "original")))
        sol = db.scalar(select(ScheduleTask).where(ScheduleTask.project_id == p.id, ScheduleTask.activity_code == "SOL"))
        weld_days = (date.fromisoformat(sol.finish) - date.fromisoformat(sol.start)).days if sol else None
        inch_km = p.diameter_in * p.length_km
        out.append(dict(
            code=p.code, name=p.name, country=p.country_code, terrain=p.terrain, diameter_in=p.diameter_in,
            length_km=p.length_km, finish_period=finish, origin=p.origin,
            final_cost_usd=cost_usd, cost_per_km_usd=cost_usd / p.length_km, cost_per_inch_km_usd=cost_usd / inch_km,
            normalized_unit_usd=cost_usd / inch_km / scale_factor(p.length_km, p.diameter_in),
            overrun_pct=k.eac / orig - 1 if orig else None, bid_margin_pct=k.bid_margin_pct,
            final_margin_pct=k.forecast_margin_pct, margin_delta_pts=k.forecast_margin_pct - k.bid_margin_pct,
            duration_months=months_between(p.start_period, finish) + 1,
            planned_months=months_between(p.start_period, p.planned_finish_period) + 1,
            delay_months=k.delay_months, welding_m_per_day=(p.length_km * 1000 / weld_days) if weld_days else None,
            weld_repair_rate=k.weld_repair_rate,
        ))
    return sorted(out, key=lambda x: (x["terrain"], x["finish_period"]))


def activity_overruns(db: Session, codes: list[str]) -> dict:
    """Median final-cost overrun per activity and terrain (closed pipelines)."""
    projects = {p.id: p for p in db.scalars(select(Project).where(Project.code.in_(codes)))}
    budget, actual = defaultdict(float), defaultdict(float)
    for b in db.scalars(select(BudgetLine).where(BudgetLine.project_id.in_(projects), BudgetLine.origin == "original")):
        budget[(b.project_id, b.activity_code)] += b.amount
    for b in db.scalars(select(BudgetLine).where(BudgetLine.project_id.in_(projects), BudgetLine.origin == "change_order")):
        budget[(b.project_id, b.activity_code)] += b.amount
    for c in db.scalars(select(CostActual).where(CostActual.project_id.in_(projects))):
        actual[(c.project_id, c.activity_code)] += c.amount
    table = defaultdict(lambda: defaultdict(list))
    for (pid, a), b in budget.items():
        if b > 0:
            table[projects[pid].terrain][a].append(actual.get((pid, a), 0.0) / b - 1)
    acts = [a for a, *_ in PIPELINE_ACTIVITIES]
    return {t: {a: (median(v[a]) if v.get(a) else None) for a in acts} for t, v in table.items()}


def benchmarks(db: Session) -> dict:
    pts = closed_pipelines(db)
    by_t = defaultdict(list)
    for x in pts:
        by_t[x["terrain"]].append(x)
    stats = {}
    for t, items in by_t.items():
        units = [x["cost_per_inch_km_usd"] for x in items]
        stats[t] = dict(
            n=len(items),
            cost_per_inch_km_p25=_pct(units, 0.25), cost_per_inch_km_p50=_pct(units, 0.5), cost_per_inch_km_p75=_pct(units, 0.75),
            cost_per_km_p50=median(x["cost_per_km_usd"] for x in items),
            overrun_p50=median(x["overrun_pct"] for x in items if x["overrun_pct"] is not None),
            margin_delta_p50=median(x["margin_delta_pts"] for x in items),
            delay_p50=median(x["delay_months"] for x in items),
            welding_m_per_day_p50=median(x["welding_m_per_day"] for x in items if x["welding_m_per_day"]) if any(x["welding_m_per_day"] for x in items) else None,
        )
    return dict(points=pts, by_terrain=stats, activity_overrun=activity_overruns(db, [x["code"] for x in pts]),
                base_year=BASE_YEAR, escalation=ESCALATION)


def estimate(db: Session, terrain: str, diameter_in: float, length_km: float, target_margin: float) -> dict:
    pts = closed_pipelines(db)
    sample = [x for x in pts if x["terrain"] == terrain]
    note = None
    if len(sample) < 2:
        sample, note = pts, "all_terrains"
    units = [x["normalized_unit_usd"] for x in sample]
    k = scale_factor(length_km, diameter_in) * diameter_in * length_km
    p25, p50, p75 = (_pct(units, q) * k for q in (0.25, 0.5, 0.75))
    overruns = [x["overrun_pct"] for x in sample if x["overrun_pct"] is not None]
    contingency = max(_pct(overruns, 0.75), 0.0) if overruns else 0.05
    cost_with_contingency = p50 * (1 + contingency)
    price = cost_with_contingency / (1 - target_margin)
    return dict(
        terrain=terrain, diameter_in=diameter_in, length_km=length_km, target_margin=target_margin,
        cost_p25=p25, cost_p50=p50, cost_p75=p75, contingency_pct=contingency,
        cost_with_contingency=cost_with_contingency, suggested_price=price,
        price_per_km=price / length_km, sample=[x["code"] for x in sample], note=note,
        historical_margin_delta=median(x["margin_delta_pts"] for x in sample),
    )
