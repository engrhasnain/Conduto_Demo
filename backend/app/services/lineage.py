"""Source previews: show the exact spreadsheet cell, PDF page or schedule task a value came from."""
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from functools import lru_cache

from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string, get_column_letter
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import DATA_DIR
from ..models import Document, DocumentChunk, Project

NS = "{http://schemas.microsoft.com/project}"


@lru_cache(maxsize=16)
def _workbook(path: str, mtime: float):
    return load_workbook(path, data_only=True)


def _display(v):
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m")
    return v


def document_meta(db: Session, doc: Document) -> dict:
    code = db.scalar(select(Project.code).where(Project.id == doc.project_id)) if doc.project_id else None
    return dict(id=doc.id, title=doc.title, filename=doc.filename, doc_type=doc.doc_type, language=doc.language,
                pages=doc.pages, period=doc.period, project_code=code, origin=doc.origin,
                file_url=f"/api/documents/{doc.id}/file")


def preview(db: Session, document_id: int, locator: str | None) -> dict | None:
    doc = db.get(Document, document_id)
    if not doc:
        return None
    path = DATA_DIR / doc.rel_path
    out = dict(document=document_meta(db, doc), locator=locator)
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xlsm"):
        wb = _workbook(str(path), path.stat().st_mtime)
        m = re.match(r"^(.*)!([A-Z]+)(\d+)$", locator or "")
        ws = wb[m.group(1)] if m and m.group(1) in wb.sheetnames else wb.worksheets[0]
        if m:
            tc, tr = column_index_from_string(m.group(2)), int(m.group(3))
        else:
            tc, tr = 1, 1
        # header row: the first row within the top 12 with 3+ text cells
        header_r = None
        for r in range(1, min(ws.max_row, 12) + 1):
            if sum(1 for c in range(1, min(ws.max_column, 12) + 1) if isinstance(ws.cell(r, c).value, str)) >= 3:
                header_r = r
                if r >= 3:
                    break
        label_cols = [c for c in (1, 2, 3, 4) if c < tc - 2]
        cols = label_cols + list(range(max(1, tc - 2), min(ws.max_column, tc + 2) + 1))
        rows_idx = list(range(max(1, tr - 4), min(ws.max_row, tr + 4) + 1))
        if header_r and header_r not in rows_idx and header_r < rows_idx[0]:
            rows_idx = [header_r] + rows_idx
        grid = []
        for r in rows_idx:
            grid.append(dict(row=r, header=r == header_r, cells=[
                dict(col=get_column_letter(c), value=_display(ws.cell(r, c).value), target=(r == tr and c == tc)) for c in cols]))
        out.update(type="sheet", sheet=ws.title, cell=f"{get_column_letter(tc)}{tr}",
                   value=_display(ws.cell(tr, tc).value), columns=[get_column_letter(c) for c in cols], grid=grid)
        return out
    if suffix == ".pdf":
        page = 1
        m = re.match(r"p\.(\d+)", locator or "")
        if m:
            page = int(m.group(1))
        chunk = db.scalar(select(DocumentChunk).where(DocumentChunk.document_id == doc.id, DocumentChunk.page == page))
        out.update(type="pdf", page=page, text=chunk.text if chunk else "", file_url=f"/api/documents/{doc.id}/file#page={page}")
        return out
    if suffix == ".xml":
        m = re.search(r"(\d+)", locator or "")
        snippet = ""
        try:
            root = ET.parse(path).getroot()
            for t in root.iter(f"{NS}Task"):
                if m and t.findtext(f"{NS}UID") == m.group(1):
                    fields = []
                    for child in t:
                        tag = child.tag.replace(NS, "")
                        if tag == "Baseline":
                            fields.append(("Baseline.Start", child.findtext(f"{NS}Start")))
                            fields.append(("Baseline.Finish", child.findtext(f"{NS}Finish")))
                        else:
                            fields.append((tag, child.text))
                    snippet = "\n".join(f"<{k}>{v}</{k}>" for k, v in fields)
                    break
        except ET.ParseError:
            pass
        out.update(type="xml", snippet=snippet)
        return out
    out.update(type="file")
    return out
