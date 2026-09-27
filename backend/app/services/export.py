"""Consolidated Excel export (Power BI / ERP ready): every fact keeps its source file and cell."""
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..i18n import activity_name
from ..models import ChangeOrder, CostActual, Document, Issue, Project, ProjectKpi
from .projects import project_detail
from .reconciliation import reconcile

HEAD_FILL = PatternFill("solid", fgColor="1F3A5F")


def _sheet(wb, title, headers, rows, widths=None):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = HEAD_FILL
    for r in rows:
        ws.append(r)
    ws.freeze_panes = "A2"
    for i, w in enumerate(widths or [], start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w
    return ws


def consolidated_workbook(db: Session, lang: str = "es") -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    docs = {d.id: d for d in db.scalars(select(Document))}
    projects = db.execute(select(Project, ProjectKpi).join(ProjectKpi, ProjectKpi.project_id == Project.id).order_by(Project.code)).all()
    _sheet(wb, "Projects", [
        "code", "name", "country", "status", "kind", "terrain", "currency", "contract_value", "contract_value_usd", "bid_margin_pct",
        "forecast_margin_pct", "margin_erosion_pts", "eac", "eac_usd", "cpi", "spi", "progress_pct", "planned_pct",
        "pending_co_value", "pending_co_usd", "delay_months", "days_lost_12m", "health", "flags"],
        [[p.code, p.name, p.country_code, p.status, p.kind, p.terrain, p.currency, p.contract_value, k.contract_value_usd,
          k.bid_margin_pct, k.forecast_margin_pct, k.margin_erosion_pts, k.eac, k.eac_usd, k.cpi, k.spi, k.progress_pct,
          k.planned_pct, k.pending_co_value, k.pending_co_usd, k.delay_months, k.days_lost_12m, k.health, k.flags] for p, k in projects],
        [10, 38, 8, 8, 9, 11, 8, 16, 16, 12, 12, 12, 16, 16, 7, 7, 10, 10, 14, 14, 10, 10, 8, 40])
    rows = []
    for p, _ in projects:
        d = project_detail(db, p.code)
        for a in d["activities"]:
            rows.append([p.code, a["code"], activity_name(a["code"], lang), p.currency, a["budget_orig"], a["budget_co"], a["bac"],
                         a["ac"], a["pct"], a["cpi"], a["eac"], a["variance"]])
    _sheet(wb, "Activities", ["project", "activity", "activity_name", "currency", "budget_original", "budget_change_orders", "bac",
                              "actual_cost", "progress_pct", "cpi", "eac", "variance"], rows, [10, 9, 30, 8, 16, 16, 16, 16, 10, 7, 16, 14])
    code = {p.id: p.code for p, _ in projects}
    _sheet(wb, "Monthly_costs", ["project", "period", "activity", "cost_type", "amount", "source_file", "source_cell"],
           [[code[c.project_id], c.period, c.activity_code, c.cost_type, c.amount,
             docs[c.document_id].filename if c.document_id in docs else None, c.locator]
            for c in db.scalars(select(CostActual).order_by(CostActual.project_id, CostActual.period))],
           [10, 9, 9, 9, 14, 38, 24])
    _sheet(wb, "Change_orders", ["project", "number", "status", "cause", "activity", "amount", "submitted", "decision", "title", "source_file"],
           [[code[c.project_id], c.number, c.status, c.cause, c.activity_code, c.amount, c.submitted_date, c.decision_date,
             {"es": c.title_es, "en": c.title_en, "pt": c.title_pt}[lang], docs[c.document_id].filename if c.document_id in docs else None]
            for c in db.scalars(select(ChangeOrder).order_by(ChangeOrder.project_id, ChangeOrder.number))],
           [10, 9, 10, 14, 9, 14, 12, 12, 60, 34])
    _sheet(wb, "Events", ["project", "period", "category", "activity", "days_lost", "cost_impact", "description", "source_file", "page"],
           [[code[i.project_id], i.period, i.category, i.activity_code, i.days_lost, i.cost_impact,
             {"es": i.description_es, "en": i.description_en, "pt": i.description_pt}[lang],
             docs[i.document_id].filename if i.document_id in docs else None, i.locator]
            for i in db.scalars(select(Issue).order_by(Issue.project_id, Issue.period))],
           [10, 9, 14, 9, 9, 14, 80, 34, 6])
    rec = reconcile(db)
    _sheet(wb, "ERP_vs_Excel", ["project", "period", "cost_type", "kind", "erp_amount", "excel_amount", "difference", "difference_usd"],
           [[d["project"], d["period"], d["cost_type"], d["kind"], d["erp_amount"], d["excel_amount"], d["diff"], d["diff_usd"]]
            for d in rec["discrepancies"]], [10, 9, 9, 18, 14, 14, 14, 14])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
