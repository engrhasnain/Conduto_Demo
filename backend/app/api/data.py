import mimetypes

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import ANTHROPIC_MODEL, DATA_DIR, SEED_VERSION, STATUS_PERIOD, ai_enabled
from ..db import get_db
from ..i18n import (ACTIVITY_NAMES, CO_CAUSES, CO_STATUS, COST_TYPES, COUNTRIES, ISSUE_CATEGORIES, TERRAINS)
from ..models import Document, Project
from ..services import benchmarks as bm
from ..services.anomalies import project_anomalies
from ..services.export import consolidated_workbook
from ..services.kpis import FLAG_RULES
from ..services.lineage import preview
from ..services.projects import activity_lineage, portfolio, project_detail
from ..services.quality import datahub
from ..services.reconciliation import reconcile

router = APIRouter(prefix="/api")


def _tri(t):
    return {"es": t[0], "en": t[1], "pt": t[2]}


@router.get("/health")
def health(db: Session = Depends(get_db)):
    return dict(status="ok", ai_enabled=ai_enabled(), model=ANTHROPIC_MODEL if ai_enabled() else None,
                status_period=STATUS_PERIOD, seed_version=SEED_VERSION,
                projects=db.scalar(select(func.count(Project.id))), documents=db.scalar(select(func.count(Document.id))))


@router.get("/meta")
def meta():
    return dict(
        status_period=STATUS_PERIOD,
        countries={k: dict(names={l: v[l] for l in ("es", "en", "pt")}, currency=v["currency"]) for k, v in COUNTRIES.items()},
        activities={k: _tri(v) for k, v in ACTIVITY_NAMES.items()},
        cost_types={k: _tri(v) for k, v in COST_TYPES.items()},
        terrains=TERRAINS,
        issue_categories={k: _tri(v) for k, v in ISSUE_CATEGORIES.items()},
        co_causes={k: _tri(v) for k, v in CO_CAUSES.items()},
        co_status={k: _tri(v) for k, v in CO_STATUS.items()},
        flags=FLAG_RULES,
    )


@router.get("/portfolio")
def get_portfolio(db: Session = Depends(get_db)):
    return portfolio(db)


@router.get("/projects/{code}")
def get_project(code: str, db: Session = Depends(get_db)):
    d = project_detail(db, code.upper())
    if not d:
        raise HTTPException(404, "Project not found")
    p = db.scalar(select(Project).where(Project.code == code.upper()))
    d["anomalies"] = project_anomalies(db, p)
    d["erp"] = reconcile(db, p.code)
    return d


@router.get("/change_orders")
def get_change_orders(status: str = "all", country: str | None = None, project: str | None = None, db: Session = Depends(get_db)):
    """All change orders across the portfolio (what sits behind the "pending change orders" figures)."""
    from datetime import date as _date
    from ..models import ChangeOrder, ProjectKpi
    from ..utils import last_day
    q = select(ChangeOrder, Project, ProjectKpi).join(Project, Project.id == ChangeOrder.project_id).join(ProjectKpi, ProjectKpi.project_id == Project.id)
    if status != "all":
        q = q.where(ChangeOrder.status == status)
    if country:
        q = q.where(Project.country_code == country.upper())
    if project:
        q = q.where(Project.code == project.upper())
    today = _date.fromisoformat(last_day(STATUS_PERIOD))
    out = []
    for co, p, k in db.execute(q):
        out.append(dict(
            project=p.code, project_name=p.name, country=p.country_code, number=co.number, status=co.status, cause=co.cause,
            activity=co.activity_code, titles={"es": co.title_es, "en": co.title_en, "pt": co.title_pt},
            amount=co.amount, currency=p.currency, amount_usd=co.amount * k.fx_usd, submitted_date=co.submitted_date,
            days_pending=(today - _date.fromisoformat(co.submitted_date)).days if co.status == "pending" else None,
            document_id=co.document_id, locator=co.locator,
        ))
    return sorted(out, key=lambda x: -x["amount_usd"])


@router.get("/documents")
def get_documents(doc_type: str | None = None, project: str | None = None, db: Session = Depends(get_db)):
    """Every source document, optionally filtered by type or project."""
    q = select(Document, Project.code).outerjoin(Project, Project.id == Document.project_id)
    if doc_type:
        q = q.where(Document.doc_type.in_(doc_type.split(",")))
    if project:
        q = q.where(Project.code == project.upper())
    return [dict(id=d.id, doc_type=d.doc_type, title=d.title, filename=d.filename, project=code, period=d.period,
                 pages=d.pages, language=d.language, origin=d.origin)
            for d, code in db.execute(q.order_by(Project.code, Document.doc_type, Document.period))]


@router.get("/datahub")
def get_datahub(db: Session = Depends(get_db)):
    return datahub(db)


@router.get("/export/consolidated.xlsx")
def export_consolidated(lang: str = "es", db: Session = Depends(get_db)):
    data = consolidated_workbook(db, lang if lang in ("es", "en", "pt") else "es")
    return Response(content=data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="Conduto_consolidado.xlsx"'})


@router.get("/projects/{code}/lineage/{activity}")
def get_activity_lineage(code: str, activity: str, db: Session = Depends(get_db)):
    d = activity_lineage(db, code.upper(), activity.upper())
    if not d:
        raise HTTPException(404, "Project not found")
    return d


@router.get("/lineage")
def get_lineage(document_id: int, locator: str | None = None, db: Session = Depends(get_db)):
    d = preview(db, document_id, locator)
    if not d:
        raise HTTPException(404, "Document not found")
    return d


@router.get("/documents/{doc_id}/file")
def get_document_file(doc_id: int, db: Session = Depends(get_db)):
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(404, "Document not found")
    path = DATA_DIR / d.rel_path
    if not path.exists():
        raise HTTPException(404, "File not found")
    media = mimetypes.guess_type(d.filename)[0] or "application/octet-stream"
    disposition = "inline" if media in ("application/pdf", "text/xml", "application/xml") else "attachment"
    return FileResponse(path, media_type=media, headers={"Content-Disposition": f'{disposition}; filename="{d.filename}"'})


@router.get("/benchmarks")
def get_benchmarks(db: Session = Depends(get_db)):
    return bm.benchmarks(db)


class EstimateIn(BaseModel):
    terrain: str = Field(pattern="^(coast|highlands|rainforest)$")
    diameter_in: float = Field(gt=2, le=60)
    length_km: float = Field(gt=0.5, le=2000)
    target_margin: float = Field(ge=0, le=0.5)


@router.post("/benchmarks/estimate")
def post_estimate(body: EstimateIn, db: Session = Depends(get_db)):
    return bm.estimate(db, body.terrain, body.diameter_in, body.length_km, body.target_margin)
