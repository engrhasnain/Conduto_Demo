"""Data Hub: what was consolidated, how complete it is, and every consistency check.

Borrowed from the grounded-extraction approach: wherever the data restates itself
(a workbook's own total row, a monthly report quoting the cumulative cost, the ERP
booking the same spend) that redundancy is used as a free, mechanical audit."""
import re
from collections import Counter, defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import ai_enabled
from ..ml import registry
from ..models import (BudgetLine, ChangeOrder, CostActual, Document, DocumentChunk, ErpTransaction, IngestionJob, Issue, Opportunity,
                      MappingTemplate, Production, Progress, Project, ProjectKpi, ScheduleTask)
from .anomalies import portfolio_anomalies
from .ingestion.normalize import parse_number
from .reconciliation import reconcile

CUM_RE = re.compile(r"(?:Costo real acumulado|Custo realizado acumulado)\s*:\s*(?:USD|S/|R\$)\s*([\d.,]+)")
FACT_MODELS = (CostActual, BudgetLine, Progress, Production, ChangeOrder, Issue, ScheduleTask, ErpTransaction, Opportunity)


def report_crosscheck(db: Session) -> dict:
    projects = {p.id: p for p in db.scalars(select(Project))}
    wb_doc = {d.project_id: d.id for d in db.scalars(select(Document).where(Document.doc_type == "cost_workbook"))}
    monthly = defaultdict(float)
    for pid, per, amt in db.execute(select(CostActual.project_id, CostActual.period, func.sum(CostActual.amount)).group_by(CostActual.project_id, CostActual.period)):
        monthly[(pid, per)] += amt
    checked, mismatches, items = 0, [], []
    rows = db.execute(select(Document, DocumentChunk).join(DocumentChunk, DocumentChunk.document_id == Document.id)
                      .where(Document.doc_type == "progress_report", DocumentChunk.page == 1)).all()
    for doc, chunk in rows:
        m = CUM_RE.search(chunk.text)
        if not m or not doc.period or doc.project_id not in projects:
            continue
        reported = parse_number(m.group(1))
        workbook = sum(v for (pid, per), v in monthly.items() if pid == doc.project_id and per <= doc.period)
        checked += 1
        p = projects[doc.project_id]
        row = dict(project=p.code, project_name=p.name, currency=p.currency, period=doc.period,
                   reported=reported, workbook=workbook, diff=reported - workbook,
                   document_id=doc.id, locator="p.1", workbook_document_id=wb_doc.get(doc.project_id))
        row["ok"] = abs(reported - workbook) <= max(1.0, workbook * 0.0005)
        items.append(row)
        if not row["ok"]:
            mismatches.append(row)
    items.sort(key=lambda r: (r["ok"], r["project"], r["period"]))
    return dict(checked=checked, matched=checked - len(mismatches), mismatches=mismatches, items=items)


def lineage_coverage(db: Session) -> dict:
    total = traced = 0
    for model in FACT_MODELS:
        total += db.scalar(select(func.count()).select_from(model)) or 0
        traced += db.scalar(select(func.count()).select_from(model).where(model.document_id.is_not(None), model.locator.is_not(None))) or 0
    return dict(total=total, traced=traced, rate=traced / total if total else 1.0)


def datahub(db: Session) -> dict:
    docs = db.scalars(select(Document)).all()
    by_type = Counter(d.doc_type for d in docs)
    by_ext = Counter(d.filename.rsplit(".", 1)[-1].lower() for d in docs)
    records = {m.__tablename__: db.scalar(select(func.count()).select_from(m)) or 0 for m in FACT_MODELS}
    records["document_pages"] = db.scalar(select(func.count()).select_from(DocumentChunk)) or 0

    projects = db.scalars(select(Project).order_by(Project.code)).all()
    per_proj = defaultdict(Counter)
    for d in docs:
        if d.project_id:
            per_proj[d.project_id][d.doc_type] += 1
    erp_projects = {pid for (pid,) in db.execute(select(ErpTransaction.project_id).distinct())}
    coverage = [dict(project=p.code, name=p.name, country=p.country_code, status=p.status, origin=p.origin,
                     docs=dict(per_proj[p.id]), erp=p.id in erp_projects) for p in projects]

    wb = [d for d in docs if d.doc_type in ("cost_workbook", "legacy_workbook") and d.checks is not None]
    codes = {p.id: p.code for p in db.scalars(select(Project))}
    workbook_checks = dict(checked=len(wb), passed=sum(1 for d in wb if d.checks.get("ok")),
                           failed=[dict(document_id=d.id, title=d.title) for d in wb if not d.checks.get("ok")],
                           items=[dict(document_id=d.id, title=d.title, filename=d.filename, project=codes.get(d.project_id), ok=bool(d.checks.get("ok")),
                                       checks=d.checks.get("checks", [])) for d in sorted(wb, key=lambda d: codes.get(d.project_id) or "")])

    rec = reconcile(db)
    fx = {p.code: k.fx_usd for p, k in db.execute(select(Project, ProjectKpi).join(ProjectKpi, ProjectKpi.project_id == Project.id))}
    anomalies = [dict(a, excess_usd=a["excess"] * fx.get(a["project"], 1.0)) for a in portfolio_anomalies(db)]
    # unexplained first: nobody documented why that money was spent
    anomalies.sort(key=lambda a: (a["explanation"] is not None, -a["excess_usd"]))
    templates = [dict(name=t.name, country=t.country_code, times_used=t.times_used, created=t.created_at.isoformat())
                 for t in db.scalars(select(MappingTemplate).order_by(MappingTemplate.id))]
    jobs = Counter(j.status for j in db.scalars(select(IngestionJob)))
    return dict(
        files=dict(total=len(docs), by_type=dict(by_type), by_ext=dict(by_ext),
                   by_language=dict(Counter(d.language for d in docs)), uploaded=sum(1 for d in docs if d.origin == "upload")),
        records=records, records_total=sum(records.values()),
        projects=len(projects), countries=len({p.country_code for p in projects}),
        coverage=coverage, templates=templates,
        quality=dict(
            lineage=lineage_coverage(db),
            workbook_totals=workbook_checks,
            report_vs_workbook=report_crosscheck(db),
            erp_vs_excel={k: v for k, v in rec.items()},
        ),
        anomalies=dict(count=len(anomalies), unexplained=sum(1 for a in anomalies if not a["explanation"]),
                       items=anomalies[:12]),
        models=registry.metrics(db),
        ingestion=dict(jobs), ai_enabled=ai_enabled(),
    )
