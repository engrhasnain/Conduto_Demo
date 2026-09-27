"""Read models for the Portfolio and Project screens."""
from collections import defaultdict
from datetime import date
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import STATUS_PERIOD
from ..i18n import ACTIVITY_NAMES
from ..models import (BudgetLine, ChangeOrder, CostActual, Document, Issue, Production, Progress, Project,
                      ProjectKpi, ScheduleTask)
from ..utils import last_day
from .kpis import compute_kpis


def _names(code: str) -> dict:
    es, en, pt = ACTIVITY_NAMES.get(code, (code, code, code))
    return {"es": es, "en": en, "pt": pt}


def project_row(p: Project, k: ProjectKpi) -> dict:
    return dict(
        code=p.code, name=p.name, country=p.country_code, client=p.client, kind=p.kind, status=p.status,
        terrain=p.terrain, region=p.region, currency=p.currency, diameter_in=p.diameter_in, length_km=p.length_km,
        start_period=p.start_period, planned_finish=p.planned_finish_period, forecast_finish=p.forecast_finish_period,
        progress_pct=k.progress_pct, planned_pct=k.planned_pct, cpi=k.cpi, spi=k.spi,
        contract_value=p.contract_value, contract_value_usd=k.contract_value_usd, revised_contract_usd=k.revised_contract_usd,
        eac_usd=k.eac_usd, ac_usd=k.ac_usd, bid_margin_pct=k.bid_margin_pct, forecast_margin_pct=k.forecast_margin_pct,
        margin_erosion_pts=k.margin_erosion_pts, forecast_margin_usd=k.forecast_margin_usd,
        pending_co_usd=k.pending_co_usd, pending_co_count=k.pending_co_count, delay_months=k.delay_months,
        days_lost_12m=k.days_lost_12m, weld_repair_rate=k.weld_repair_rate, cost_overrun_pct=k.cost_overrun_pct,
        flags=[f for f in k.flags.split(",") if f], health=k.health, origin=p.origin, manager=p.manager,
    )


def portfolio(db: Session) -> dict:
    rows = db.execute(select(Project, ProjectKpi).join(ProjectKpi, ProjectKpi.project_id == Project.id).order_by(Project.code)).all()
    projects = [project_row(p, k) for p, k in rows]
    active = [x for x in projects if x["status"] == "active"]

    def wavg(items, key, weight):
        tw = sum(i[weight] for i in items)
        return sum(i[key] * i[weight] for i in items) / tw if tw else None

    summary = dict(
        active_count=len(active), closed_count=len(projects) - len(active),
        active_contract_usd=sum(x["contract_value_usd"] for x in active),
        active_revised_usd=sum(x["revised_contract_usd"] for x in active),
        active_eac_usd=sum(x["eac_usd"] for x in active),
        active_forecast_margin_pct=(sum(x["forecast_margin_usd"] for x in active) / sum(x["revised_contract_usd"] for x in active)) if active else None,
        active_bid_margin_pct=wavg(active, "bid_margin_pct", "contract_value_usd"),
        pending_co_usd=sum(x["pending_co_usd"] for x in projects),
        pending_co_count=sum(x["pending_co_count"] for x in projects),
        health={h: sum(1 for x in active if x["health"] == h) for h in ("red", "amber", "green")},
        days_lost_12m=sum(x["days_lost_12m"] for x in active),
    )
    by_country = []
    for c in ("EC", "PE", "BR"):
        items = [x for x in projects if x["country"] == c]
        act = [x for x in items if x["status"] == "active"]
        by_country.append(dict(
            country=c, projects=len(items), active=len(act),
            active_contract_usd=sum(x["contract_value_usd"] for x in act),
            forecast_margin_pct=(sum(x["forecast_margin_usd"] for x in act) / sum(x["revised_contract_usd"] for x in act)) if act else None,
            pending_co_usd=sum(x["pending_co_usd"] for x in items),
        ))
    return dict(status_period=STATUS_PERIOD, summary=summary, by_country=by_country, projects=projects,
                insights=insights(db, projects))


def insights(db: Session, projects: list[dict]) -> list[dict]:
    out = []
    active = [x for x in projects if x["status"] == "active"]
    if active:
        worst = max(active, key=lambda x: x["margin_erosion_pts"])
        rev = worst["revised_contract_usd"] or 1
        out.append(dict(code="worst_project", severity="red", project=worst["code"], params=dict(
            name=worst["name"], bid=worst["bid_margin_pct"], forecast=worst["forecast_margin_pct"],
            erosion=worst["margin_erosion_pts"], pending_usd=worst["pending_co_usd"],
            recover_pts=worst["pending_co_usd"] / rev)))
    today = date.fromisoformat(last_day(STATUS_PERIOD))
    pending = db.execute(select(ChangeOrder, Project).join(Project, Project.id == ChangeOrder.project_id).where(ChangeOrder.status == "pending")).all()
    kmap = {x["code"]: x for x in projects}
    total = aged = aged_n = 0.0
    for co, p in pending:
        usd = co.amount * (kmap[p.code]["contract_value_usd"] / p.contract_value)
        total += usd
        if (today - date.fromisoformat(co.submitted_date)).days > 90:
            aged += usd
            aged_n += 1
    if pending:
        out.append(dict(code="pending_cos", severity="amber", params=dict(total_usd=total, count=len(pending), aged_usd=aged, aged_count=int(aged_n))))
    by_t = defaultdict(list)
    for x in projects:
        if x["status"] == "closed" and x["kind"] == "pipeline":
            by_t[x["terrain"]].append(x["margin_erosion_pts"])
    if by_t.get("rainforest") and by_t.get("coast"):
        out.append(dict(code="terrain_erosion", severity="info", params=dict(
            rainforest=median(by_t["rainforest"]), coast=median(by_t["coast"]),
            highlands=median(by_t["highlands"]) if by_t.get("highlands") else None,
            n=sum(len(v) for v in by_t.values()))))
    return out


def project_detail(db: Session, code: str) -> dict | None:
    p = db.scalar(select(Project).where(Project.code == code))
    if not p:
        return None
    k = db.get(ProjectKpi, p.id)
    full = compute_kpis(db, p)
    s, f = full["_evm"], full["_facts"]
    rate = full["fx_usd"]

    activities = []
    for a, v in s["activities"].items():
        activities.append(dict(
            code=a, names=_names(a), bac=v["bac"], budget_orig=f["budget_orig"].get(a, 0.0), budget_co=f["budget_co"].get(a, 0.0),
            ac=v["ac"], ev=v["ev"], pv=v["pv"], eac=v["eac"], pct=v["pct"], planned=v["planned"], cpi=v["cpi"],
            variance=v["eac"] - v["bac"],
        ))
    order = {c: i for i, c in enumerate(ACTIVITY_NAMES)}
    activities.sort(key=lambda x: order.get(x["code"], 99))

    orig_total = sum(f["budget_orig"].values())
    co_rev = full["approved_co_value"]
    co_budget = sum(f["budget_co"].values())
    steps = [dict(key="bid_margin", value=p.contract_value - orig_total)]
    if co_rev:
        steps.append(dict(key="approved_cos", value=co_rev - co_budget))
    variances = sorted(activities, key=lambda x: -abs(x["variance"]))
    top, rest = variances[:5], variances[5:]
    for x in sorted(top, key=lambda x: x["variance"], reverse=True):
        steps.append(dict(key="activity", code=x["code"], value=-x["variance"]))
    if rest:
        steps.append(dict(key="other", value=-sum(x["variance"] for x in rest)))
    steps.append(dict(key="forecast_margin", value=full["forecast_margin_value"]))
    waterfall = dict(steps=steps, revised_contract=full["revised_contract"], pending_recovery=full["pending_co_value"])

    # S-curve (cumulative, project currency)
    prog = defaultdict(dict)
    for pr in db.scalars(select(Progress).where(Progress.project_id == p.id)):
        prog[pr.period][pr.activity_code] = (pr.planned_pct, pr.actual_pct)
    periods = sorted(set(prog) | set(f["monthly"]))
    scurve, cum = [], 0.0
    for per in periods:
        cum += f["monthly"].get(per, 0.0)
        pv = sum(prog[per].get(a, (None, None))[0] * f["bac"][a] for a in f["bac"] if a in prog[per]) if per in prog else None
        ev = sum((prog[per][a][1] or 0) * f["bac"][a] for a in f["bac"] if a in prog[per]) if per in prog else None
        scurve.append(dict(period=per, pv=pv, ev=ev, ac=cum if per <= full["as_of_period"] else None, month_cost=f["monthly"].get(per, 0.0)))

    today = date.fromisoformat(last_day(full["as_of_period"]))
    cos = []
    for c in sorted(f["cos"], key=lambda c: c.submitted_date):
        days_pending = (today - date.fromisoformat(c.submitted_date)).days if c.status == "pending" else None
        cos.append(dict(id=c.id, number=c.number, titles={"es": c.title_es, "en": c.title_en, "pt": c.title_pt}, cause=c.cause,
                        activity=c.activity_code, amount=c.amount, amount_usd=c.amount * rate, status=c.status,
                        submitted_date=c.submitted_date, decision_date=c.decision_date, days_pending=days_pending,
                        schedule_impact_days=c.schedule_impact_days, document_id=c.document_id, locator=c.locator))
    issues = [dict(id=i.id, period=i.period, category=i.category, activity=i.activity_code, days_lost=i.days_lost,
                   cost_impact=i.cost_impact, descriptions={"es": i.description_es, "en": i.description_en, "pt": i.description_pt},
                   document_id=i.document_id, locator=i.locator)
              for i in sorted(f["issues"], key=lambda i: i.period)]
    tasks = [dict(uid=t.uid, name=t.name, activity=t.activity_code, baseline_start=t.baseline_start, baseline_finish=t.baseline_finish,
                  start=t.start, finish=t.finish, pct=t.pct_complete, document_id=t.document_id, locator=t.locator)
             for t in db.scalars(select(ScheduleTask).where(ScheduleTask.project_id == p.id).order_by(ScheduleTask.uid))]
    production, prev = [], None
    for pr in f["production"]:
        new_w = pr.welds_cum - (prev.welds_cum if prev else 0)
        new_r = pr.weld_repairs_cum - (prev.weld_repairs_cum if prev else 0)
        production.append(dict(period=pr.period, km=pr.km_welded_cum, welds=pr.welds_cum, repairs=pr.weld_repairs_cum,
                               repair_rate=new_r / new_w if new_w > 0 else None, document_id=pr.document_id, locator=pr.locator))
        prev = pr
    docs = [dict(id=d.id, doc_type=d.doc_type, title=d.title, filename=d.filename, language=d.language, pages=d.pages,
                 period=d.period, origin=d.origin)
            for d in db.scalars(select(Document).where(Document.project_id == p.id).order_by(Document.doc_type, Document.period))]

    drivers = []
    erosion_total = sum(max(x["variance"], 0) for x in activities) or 1
    for x in sorted(activities, key=lambda x: -x["variance"])[:4]:
        if x["variance"] <= 0:
            continue
        drivers.append(dict(
            activity=x["code"], variance=x["variance"], share=x["variance"] / erosion_total,
            cos=[c["number"] for c in cos if c["activity"] == x["code"] and c["status"] != "approved"],
            issues=[i["id"] for i in issues if i["activity"] == x["code"]],
            standby_cost=sum(i["cost_impact"] for i in issues if i["activity"] == x["code"]),
            days_lost=sum(i["days_lost"] for i in issues if i["activity"] == x["code"]),
        ))

    header = project_row(p, k)
    header.update(
        descriptions={"es": p.description_es, "en": p.description_en, "pt": p.description_pt},
        contract_type=p.contract_type, fx_usd=rate, as_of_period=full["as_of_period"],
        contract_source=dict(document_id=p.contract_document_id, locator=p.contract_locator),
        bid_margin_source=dict(document_id=p.bid_margin_document_id, locator=p.bid_margin_locator),
    )
    kpis = {key: v for key, v in full.items() if not key.startswith("_")}
    kpis["flags"] = [x for x in kpis["flags"].split(",") if x]
    kpis["oldest_pending_days"] = full["_oldest_pending_days"]
    return dict(project=header, kpis=kpis, activities=activities, waterfall=waterfall, scurve=scurve,
                change_orders=cos, issues=issues, schedule=tasks, production=production, documents=docs, drivers=drivers)


def activity_lineage(db: Session, code: str, activity: str) -> dict | None:
    p = db.scalar(select(Project).where(Project.code == code))
    if not p:
        return None
    budget = [dict(cost_type=b.cost_type, amount=b.amount, origin=b.origin, co_number=b.co_number, document_id=b.document_id, locator=b.locator)
              for b in db.scalars(select(BudgetLine).where(BudgetLine.project_id == p.id, BudgetLine.activity_code == activity))]
    costs = [dict(period=c.period, cost_type=c.cost_type, amount=c.amount, document_id=c.document_id, locator=c.locator)
             for c in db.scalars(select(CostActual).where(CostActual.project_id == p.id, CostActual.activity_code == activity)
                                 .order_by(CostActual.period.desc(), CostActual.cost_type))]
    progress = db.scalars(select(Progress).where(Progress.project_id == p.id, Progress.activity_code == activity)
                          .order_by(Progress.period.desc())).first()
    return dict(project=code, activity=activity, names=_names(activity), currency=p.currency, budget=budget, costs=costs,
                progress=dict(period=progress.period, pct=progress.actual_pct, planned=progress.planned_pct,
                              document_id=progress.document_id, locator=progress.locator) if progress else None)
