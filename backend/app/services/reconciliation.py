"""ERP (Dynamics GP) vs project-control Excel, at project x month x cost-type level."""
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CostActual, ErpTransaction, Project, ProjectKpi


def reconcile(db: Session, project_code: str | None = None) -> dict:
    projects = {p.id: p for p in db.scalars(select(Project))}
    fx = {k.project_id: k.fx_usd for k in db.scalars(select(ProjectKpi))}
    erp = defaultdict(float)
    erp_rows = defaultdict(list)
    for t in db.scalars(select(ErpTransaction)):
        if project_code and projects[t.project_id].code != project_code:
            continue
        key = (t.project_id, t.period, t.cost_type)
        erp[key] += t.debit - t.credit
        erp_rows[key].append(t)
    if not erp:
        return dict(cells=0, matched=0, match_rate=None, erp_total_usd=0.0, discrepancies=[], projects=0)
    scope = {(pid, per) for pid, per, _ in erp}
    excel = defaultdict(float)
    excel_cells = defaultdict(list)
    for c in db.scalars(select(CostActual).where(CostActual.project_id.in_({pid for pid, _ in scope}))):
        if (c.project_id, c.period) in scope:
            key = (c.project_id, c.period, c.cost_type)
            excel[key] += c.amount
            excel_cells[key].append(c)

    discrepancies, matched, abs_diff, erp_total_usd = [], 0, 0.0, 0.0
    for key in sorted(set(erp) | set(excel)):
        pid, per, ct = key
        e, x = erp.get(key, 0.0), excel.get(key, 0.0)
        rate = fx.get(pid, 1.0)
        erp_total_usd += e * rate
        diff = e - x
        if abs(diff) < 1.0:
            matched += 1
            continue
        abs_diff += abs(diff) * rate
        rows = erp_rows.get(key, [])
        seen, dup = {}, None
        for r in rows:
            k = (r.reference, round(r.debit, 2))
            if k in seen:
                dup = (seen[k], r)
                break
            seen[k] = r
        if dup and abs(diff - dup[1].debit) < 1.0:
            kind, shown = "duplicate", list(dup)
        elif diff > 0:
            kind = "missing_in_excel"
            shown = [r for r in rows if abs(r.debit - diff) < 1.0] or sorted(rows, key=lambda r: -r.debit)[:2]
        else:
            kind, shown = "missing_in_erp", sorted(rows, key=lambda r: -r.debit)[:2]
        p = projects[pid]
        discrepancies.append(dict(
            project=p.code, project_name=p.name, currency=p.currency, period=per, cost_type=ct, kind=kind,
            erp_amount=e, excel_amount=x, diff=diff, diff_usd=diff * rate,
            erp_rows=[dict(reference=r.reference, vendor=r.vendor, trx_date=r.trx_date, account=r.account, amount=r.debit,
                           document_id=r.document_id, locator=r.locator) for r in shown],
            excel_cells=[dict(activity=c.activity_code, amount=c.amount, document_id=c.document_id, locator=c.locator)
                         for c in sorted(excel_cells.get(key, []), key=lambda c: -c.amount)[:3]],
        ))
    cells = len(set(erp) | set(excel))
    return dict(
        cells=cells, matched=matched, projects=len({pid for pid, _, _ in erp}),
        match_rate=1 - abs_diff / erp_total_usd if erp_total_usd else None,
        erp_total_usd=erp_total_usd, erp_transactions=sum(len(v) for v in erp_rows.values()),
        discrepancies=sorted(discrepancies, key=lambda d: -abs(d["diff_usd"])),
    )
