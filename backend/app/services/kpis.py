"""Project KPIs computed from canonical facts and materialized in `project_kpis`."""
from collections import defaultdict
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import STATUS_PERIOD
from ..models import (BudgetLine, ChangeOrder, CostActual, FxRate, Issue, Production, Progress,
                      Project, ProjectKpi)
from ..utils import add_months, last_day, months_between
from .evm import evm_summary

FLAG_RULES = {
    "COST_OVERRUN": "CPI below 0.95",
    "SCHEDULE_DELAY": "SPI below 0.92 or forecast finish 3+ months late",
    "MARGIN_EROSION": "forecast margin 3+ points below bid margin",
    "PENDING_CO": "pending change orders worth 3%+ of the contract",
    "PENDING_CO_AGING": "a change order pending for more than 90 days",
    "WELD_QUALITY": "cumulative weld repair rate above 5%",
}


def fx_table(db: Session) -> dict:
    return {(r.currency, r.period): r.usd_per_unit for r in db.scalars(select(FxRate))}


def fx_for(fx: dict, currency: str, period: str) -> float:
    if currency == "USD":
        return 1.0
    p = period
    for _ in range(36):
        if (currency, p) in fx:
            return fx[(currency, p)]
        p = add_months(p, -1)
    raise KeyError(f"No FX for {currency} {period}")


def as_of_period(db: Session, project: Project) -> str:
    if project.status == "active":
        return STATUS_PERIOD
    periods = db.scalars(select(CostActual.period).where(CostActual.project_id == project.id)).all()
    return max(periods) if periods else project.forecast_finish_period


def project_facts(db: Session, project: Project, as_of: str) -> dict:
    pid = project.id
    budget_orig, budget_co, bac = defaultdict(float), defaultdict(float), defaultdict(float)
    for b in db.scalars(select(BudgetLine).where(BudgetLine.project_id == pid)):
        bac[b.activity_code] += b.amount
        (budget_orig if b.origin == "original" else budget_co)[b.activity_code] += b.amount
    ac, monthly = defaultdict(float), defaultdict(float)
    for c in db.scalars(select(CostActual).where(CostActual.project_id == pid, CostActual.period <= as_of)):
        ac[c.activity_code] += c.amount
        monthly[c.period] += c.amount
    pct, planned = {}, {}
    latest = {}
    for p in db.scalars(select(Progress).where(Progress.project_id == pid, Progress.period <= as_of)):
        if p.activity_code not in latest or p.period > latest[p.activity_code]:
            latest[p.activity_code] = p.period
            pct[p.activity_code] = p.actual_pct if p.actual_pct is not None else 0.0
            planned[p.activity_code] = p.planned_pct
    cos = db.scalars(select(ChangeOrder).where(ChangeOrder.project_id == pid)).all()
    issues = db.scalars(select(Issue).where(Issue.project_id == pid)).all()
    prod = db.scalars(select(Production).where(Production.project_id == pid, Production.period <= as_of).order_by(Production.period)).all()
    return dict(budget_orig=budget_orig, budget_co=budget_co, bac=bac, ac=ac, monthly=monthly,
                pct=pct, planned=planned, cos=cos, issues=issues, production=prod)


def compute_kpis(db: Session, project: Project, fx: dict | None = None) -> dict:
    fx = fx or fx_table(db)
    as_of = as_of_period(db, project)
    f = project_facts(db, project, as_of)
    closed = project.status == "closed"
    s = evm_summary(dict(f["bac"]), dict(f["ac"]), f["pct"], f["planned"], closed)

    approved = sum(c.amount for c in f["cos"] if c.status == "approved")
    pending_cos = [c for c in f["cos"] if c.status == "pending"]
    pending = sum(c.amount for c in pending_cos)
    revised = project.contract_value + approved
    margin_value = revised - s["eac"]
    margin_pct = margin_value / revised if revised else 0.0
    erosion = project.bid_margin_pct - margin_pct
    rate = fx_for(fx, project.currency, STATUS_PERIOD)

    weld_rate = None
    if f["production"]:
        last = f["production"][-1]
        weld_rate = last.weld_repairs_cum / last.welds_cum if last.welds_cum else None

    window_start = add_months(as_of, -11)
    days_lost = sum(i.days_lost for i in f["issues"] if window_start <= i.period <= as_of)
    delay = months_between(project.planned_finish_period, project.forecast_finish_period)

    as_of_end = date.fromisoformat(last_day(as_of))
    oldest_pending = max(((as_of_end - date.fromisoformat(c.submitted_date)).days for c in pending_cos), default=0)

    flags = []
    if not closed and s["cpi"] is not None and s["cpi"] < 0.95:
        flags.append("COST_OVERRUN")
    if not closed and ((s["spi"] is not None and s["spi"] < 0.92) or delay >= 3):
        flags.append("SCHEDULE_DELAY")
    if erosion >= 0.03 - 1e-6:
        flags.append("MARGIN_EROSION")
    if pending >= 0.03 * project.contract_value:
        flags.append("PENDING_CO")
    if oldest_pending > 90:
        flags.append("PENDING_CO_AGING")
    if weld_rate is not None and weld_rate > 0.05:
        flags.append("WELD_QUALITY")

    if erosion >= 0.08 or len(flags) >= 3:
        health = "red"
    elif flags or erosion >= 0.03:
        health = "amber"
    else:
        health = "green"

    bac_total = s["bac"]
    return dict(
        as_of_period=as_of, progress_pct=s["progress"], planned_pct=s["planned"],
        bac=bac_total, ac=s["ac"], ev=s["ev"], pv=s["pv"], eac=s["eac"],
        cpi=None if closed else s["cpi"], spi=None if closed else s["spi"],
        revised_contract=revised, approved_co_value=approved, pending_co_value=pending,
        pending_co_count=len(pending_cos), forecast_margin_value=margin_value,
        forecast_margin_pct=margin_pct, bid_margin_pct=project.bid_margin_pct,
        margin_erosion_pts=erosion, fx_usd=rate,
        contract_value_usd=project.contract_value * rate, revised_contract_usd=revised * rate,
        ac_usd=s["ac"] * rate, eac_usd=s["eac"] * rate, forecast_margin_usd=margin_value * rate,
        pending_co_usd=pending * rate,
        cost_overrun_pct=(s["eac"] / bac_total - 1) if bac_total else 0.0,
        weld_repair_rate=weld_rate, days_lost_12m=days_lost, delay_months=delay,
        flags=",".join(flags), health=health,
        # not persisted
        _evm=s, _facts=f, _oldest_pending_days=oldest_pending,
    )


def refresh_kpis(db: Session, project_ids: list[int] | None = None):
    fx = fx_table(db)
    q = select(Project)
    if project_ids:
        q = q.where(Project.id.in_(project_ids))
    for project in db.scalars(q).all():
        k = compute_kpis(db, project, fx)
        db.execute(delete(ProjectKpi).where(ProjectKpi.project_id == project.id))
        db.add(ProjectKpi(project_id=project.id, **{key: v for key, v in k.items() if not key.startswith("_")}))
    db.commit()
