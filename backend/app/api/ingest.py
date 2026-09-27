import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import DATA_DIR, INBOX_DIR
from ..db import get_db
from ..models import IngestionJob
from ..seed.inbox import SAMPLES
from ..services.ingestion.service import IngestError, analyze, confirm

router = APIRouter(prefix="/api/ingest")
MAX_BYTES = 4 * 1024 * 1024  # Vercel rejects request bodies above 4.5 MB
ALLOWED = {".xlsx", ".xlsm", ".pdf", ".xml"}


def job_out(job: IngestionJob) -> dict:
    return dict(id=job.id, filename=job.filename, status=job.status, file_kind=job.file_kind, ai_used=job.ai_used,
                created_at=job.created_at.isoformat() + "Z", preview=job.preview, result=job.result)


@router.get("/samples")
def samples():
    out = []
    for s in SAMPLES:
        p = INBOX_DIR / s["filename"]
        out.append(dict(filename=s["filename"], kind=s["kind"], size=p.stat().st_size if p.exists() else 0,
                        description={"es": s["es"], "en": s["en"], "pt": s["pt"]}))
    return out


def _sample_path(filename: str) -> Path:
    if filename not in {s["filename"] for s in SAMPLES}:
        raise HTTPException(404, "Unknown sample")
    p = INBOX_DIR / filename
    if not p.exists():
        raise HTTPException(404, "Sample file missing; reset the demo data")
    return p


@router.get("/samples/{filename}/file")
def sample_file(filename: str):
    p = _sample_path(filename)
    return FileResponse(p, filename=filename)


@router.post("/samples/{filename}")
def analyze_sample(filename: str, db: Session = Depends(get_db)):
    return job_out(analyze(db, _sample_path(filename), filename))


@router.post("/upload")
async def upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    name = file.filename or "upload"
    if Path(name).suffix.lower() not in ALLOWED:
        raise HTTPException(400, "Supported files: Excel (.xlsx), PDF and Microsoft Project (.xml)")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File too large (maximum 4 megabytes)")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp) / Path(name).name
        tmp_path.write_bytes(data)
        return job_out(analyze(db, tmp_path, name))


class ConfirmIn(BaseModel):
    project_code: str | None = None
    row_mapping: dict[str, str | None] = {}
    project: dict = {}
    fields: dict = {}
    template_name: str | None = None


@router.post("/jobs/{job_id}/confirm")
def confirm_job(job_id: int, body: ConfirmIn, db: Session = Depends(get_db)):
    try:
        result = confirm(db, job_id, body.model_dump())
    except IngestError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return dict(result=result, job=job_out(db.get(IngestionJob, job_id)))


@router.get("/jobs")
def jobs(db: Session = Depends(get_db)):
    rows = db.scalars(select(IngestionJob).order_by(IngestionJob.id.desc()).limit(30)).all()
    return [dict(id=j.id, filename=j.filename, status=j.status, file_kind=j.file_kind, ai_used=j.ai_used,
                 created_at=j.created_at.isoformat() + "Z", project_code=(j.result or {}).get("project_code") or ((j.preview or {}).get("project") or {}).get("code"))
            for j in rows]


@router.get("/jobs/{job_id}/file")
def job_file(job_id: int, db: Session = Depends(get_db)):
    j = db.get(IngestionJob, job_id)
    if not j:
        raise HTTPException(404, "Job not found")
    path = DATA_DIR / j.stored_path
    media = "application/pdf" if path.suffix.lower() == ".pdf" else "application/octet-stream"
    return FileResponse(path, media_type=media, headers={"Content-Disposition": f'inline; filename="{j.filename}"'})


@router.get("/jobs/{job_id}")
def job(job_id: int, db: Session = Depends(get_db)):
    j = db.get(IngestionJob, job_id)
    if not j:
        raise HTTPException(404, "Job not found")
    return job_out(j)
