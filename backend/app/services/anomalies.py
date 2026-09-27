"""Detects months where an activity spent far more than its physical progress justifies
("cost without progress": standby, rework, unapproved extra work) and links each one
to the event or change order that explains it, or flags it as unexplained.

Expected cost = progress gained x activity budget x the activity's own typical cost
rate (median across its months). A month is anomalous when the excess is above
4 robust deviations and above 0.3% of the project budget."""
from collections import defaultdict
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import BudgetLine, ChangeOrder, CostActual, Issue, Progress, Project
from ..utils import add_months

MIN_SHARE_OF_BUDGET = 0.003
# Change orders for extra work explain extra spend; standby or price claims do not (no work executed).
WORK_CAUSES = {"client_request", "design", "geotech", "scope"}


def project_anomalies(db: Session, project: Project) -> list[dict]:
    pid = project.id
    bac = defaultdict(float)
    for b in db.scalars(select(BudgetLine).where(BudgetLine.project_id == pid)):
        bac[b.activity_code] += b.amount
    total_bac = sum(bac.values())
    cost = defaultdict(float)
    top_cell: dict = {}
    for c in db.scalars(select(CostActual).where(CostActual.project_id == pid)):
        key = (c.activity_code, c.period)
        cost[key] += c.amount
        if key not in top_cell or c.amount > top_cell[key][0]:
            top_cell[key] = (c.amount, c.document_id, c.locator)
    pct = {(p.activity_code, p.period): p.actual_pct or 0.0 for p in db.scalars(select(Progress).where(Progress.project_id == pid))}
    periods = sorted({p for _, p in pct} | {p for _, p in cost})
    if len(periods) < 4 or not total_bac:
        return []
    issues = db.scalars(select(Issue).where(Issue.project_id == pid)).all()
    cos = db.scalars(select(ChangeOrder).where(ChangeOrder.project_id == pid, ChangeOrder.status != "approved")).all()

    out = []
    for a, b in bac.items():
        if b <= 0:
            continue
        rows = []
        prev = 0.0
        for per in periods:
            cur = pct.get((a, per), prev)
            rows.append((per, cost.get((a, per), 0.0), max(cur - prev, 0.0)))
            prev = cur
        rates = [c / (d * b) for _, c, d in rows if d > 0.02 and c > 0]
        if len(rates) < 3:
            continue
        rate = median(rates)
        resid = [(per, c, c - d * b * rate, d) for per, c, d in rows if c > 0]
        mad = median(abs(r - median([x[2] for x in resid])) for _, _, r, _ in resid) or 1.0
        threshold = max(4 * 1.4826 * mad, MIN_SHARE_OF_BUDGET * total_bac)
        for per, c, excess, d in resid:
            if excess <= threshold:
                continue
            _, doc, loc = top_cell.get((a, per), (0, None, None))
            item = dict(period=per, activity=a, cost=c, expected=c - excess, excess=excess, progress_gain=d,
                        document_id=doc, locator=loc, explanation=None)
            issue = next((i for i in issues if i.period == per and i.activity_code == a), None)
            if issue:
                item["explanation"] = dict(kind="issue", category=issue.category, days_lost=issue.days_lost,
                                           descriptions={"es": issue.description_es, "en": issue.description_en, "pt": issue.description_pt},
                                           document_id=issue.document_id, locator=issue.locator)
            else:
                co = next((x for x in cos if x.activity_code == a and x.cause in WORK_CAUSES
                           and add_months(x.submitted_date[:7], -2) <= per <= x.submitted_date[:7]), None)
                if co:
                    item["explanation"] = dict(kind="change_order", number=co.number, status=co.status,
                                               titles={"es": co.title_es, "en": co.title_en, "pt": co.title_pt},
                                               document_id=co.document_id, locator=co.locator)
            out.append(item)
    return sorted(out, key=lambda x: -x["excess"])


def portfolio_anomalies(db: Session, active_only: bool = True) -> list[dict]:
    q = select(Project)
    if active_only:
        q = q.where(Project.status == "active")
    out = []
    for p in db.scalars(q):
        for a in project_anomalies(db, p):
            out.append(dict(a, project=p.code, project_name=p.name, currency=p.currency))
    return out
