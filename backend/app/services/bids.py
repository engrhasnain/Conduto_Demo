"""Bid pipeline: opportunities from the sales-system connector, each open bid checked against history.

The check answers one question: if this job costs what similar closed jobs really cost, what margin is left?
- the bid's own assumption: value × (1 − planned margin) = the cost the bid can afford;
- history: the median cost of comparable closed pipelines (same terrain, scaled by diameter and length, in today's dollars);
- risk: red when the margin left at the historical cost is under 6%; amber when the bid assumes a cost more than 3% below
  history; green otherwise. Civil works have no comparable history yet, so they are listed without a check.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Opportunity
from .benchmarks import closed_pipelines, estimate
from .connectors import _runs, fx_usd, now

OPEN = ("prospecting", "preparing", "submitted", "negotiation")
RED_MARGIN = 0.06
AMBER_GAP = -0.03


def check(db: Session, o: Opportunity, value_usd: float) -> dict:
    if o.kind != "pipeline" or not o.diameter_in or not o.length_km:
        return dict(risk="none", reason="no_history")
    e = estimate(db, o.terrain, o.diameter_in, o.length_km, o.bid_margin_pct)
    hist = e["cost_p50"]
    affordable = value_usd * (1 - o.bid_margin_pct)
    gap = affordable / hist - 1
    margin_left = 1 - hist / value_usd
    price_needed = hist / (1 - o.bid_margin_pct)
    risk = "red" if margin_left < RED_MARGIN else "amber" if gap < AMBER_GAP else "green"
    return dict(
        risk=risk, affordable_cost_usd=affordable, history_cost_usd=hist, history_low_usd=e["cost_p25"], history_high_usd=e["cost_p75"],
        gap=gap, margin_left=margin_left, typical_erosion=e["historical_margin_delta"], contingency=e["contingency_pct"],
        price_needed_usd=price_needed, price_gap_usd=price_needed - value_usd, sample=e["sample"], note=e["note"],
    )


def _row(db: Session, o: Opportunity, fx: dict) -> dict:
    rate = fx.setdefault(o.currency, fx_usd(db, o.currency))
    value_usd = o.value * rate
    row = dict(
        crm_id=o.crm_id, name=o.name, client=o.client, country=o.country_code, kind=o.kind, terrain=o.terrain, region=o.region,
        diameter_in=o.diameter_in, length_km=o.length_km, stage=o.stage, currency=o.currency, value=o.value, value_usd=value_usd,
        bid_margin_pct=o.bid_margin_pct, probability=o.probability, weighted_usd=value_usd * o.probability,
        expected_decision=o.expected_decision, owner=o.owner, next_step={"es": o.next_step_es, "en": o.next_step_en, "pt": o.next_step_pt},
        project_code=o.project_code, lost_reason=o.lost_reason, modified_on=o.modified_on, document_id=o.document_id, locator=o.locator,
    )
    if o.stage in OPEN:
        row["check"] = check(db, o, value_usd)
    return row


def pipeline(db: Session) -> dict:
    fx: dict = {}
    rows = [_row(db, o, fx) for o in db.scalars(select(Opportunity).order_by(Opportunity.expected_decision, Opportunity.crm_id))]
    open_ = [r for r in rows if r["stage"] in OPEN]
    won = [r for r in rows if r["stage"] == "won"]
    lost = [r for r in rows if r["stage"] == "lost"]
    red = [r for r in open_ if r["check"]["risk"] == "red"]
    amber = [r for r in open_ if r["check"]["risk"] == "amber"]
    runs = _runs(db, "sales", now(), limit=1)
    return dict(
        bids=rows,
        summary=dict(
            open_count=len(open_), open_value_usd=sum(r["value_usd"] for r in open_), weighted_usd=sum(r["weighted_usd"] for r in open_),
            red_count=len(red), red_value_usd=sum(r["value_usd"] for r in red), amber_count=len(amber),
            amber_value_usd=sum(r["value_usd"] for r in amber),
            won_count=len(won), won_value_usd=sum(r["value_usd"] for r in won), lost_count=len(lost),
            win_rate=len(won) / (len(won) + len(lost)) if won or lost else None,
        ),
        last_sync=runs[0] if runs else None,
    )


def bid_detail(db: Session, crm_id: str) -> dict | None:
    o = db.scalar(select(Opportunity).where(Opportunity.crm_id == crm_id.upper()))
    if not o:
        return None
    row = _row(db, o, {})
    chk = row.get("check") or {}
    if chk.get("sample"):
        by_code = {p["code"]: p for p in closed_pipelines(db)}
        row["comparables"] = [dict(code=c, name=by_code[c]["name"], country=by_code[c]["country"], diameter_in=by_code[c]["diameter_in"],
                                   length_km=by_code[c]["length_km"], cost_per_km_usd=by_code[c]["cost_per_km_usd"],
                                   margin_delta_pts=by_code[c]["margin_delta_pts"], overrun_pct=by_code[c]["overrun_pct"])
                              for c in chk["sample"] if c in by_code]
    return row

