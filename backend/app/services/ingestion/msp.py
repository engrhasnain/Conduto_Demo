"""MS Project XML (MSPDI) reader. Native .mpp files would go through MPXJ in production."""
import re
import xml.etree.ElementTree as ET

from .mapping import map_activity

NS = "{http://schemas.microsoft.com/project}"
PROJECT_CODE_RE = re.compile(r"\b([A-Z]{2}-\d{4})\b")


def _d(v: str | None) -> str | None:
    return v[:10] if v else None


def parse_mspdi(path) -> dict:
    root = ET.parse(path).getroot()
    title = root.findtext(f"{NS}Title") or root.findtext(f"{NS}Name") or ""
    m = PROJECT_CODE_RE.search(title) or PROJECT_CODE_RE.search(root.findtext(f"{NS}Name") or "")
    tasks = []
    for t in root.iter(f"{NS}Task"):
        if t.findtext(f"{NS}Summary") == "1" or t.findtext(f"{NS}UID") == "0":
            continue
        name = t.findtext(f"{NS}Name") or ""
        base = t.find(f"{NS}Baseline")
        mp = map_activity(name)
        tasks.append(dict(
            uid=int(t.findtext(f"{NS}UID") or 0), name=name,
            start=_d(t.findtext(f"{NS}Start")), finish=_d(t.findtext(f"{NS}Finish")),
            baseline_start=_d(base.findtext(f"{NS}Start")) if base is not None else None,
            baseline_finish=_d(base.findtext(f"{NS}Finish")) if base is not None else None,
            pct=float(t.findtext(f"{NS}PercentComplete") or 0) / 100,
            activity_code=mp["code"], confidence=mp["confidence"], method=mp["method"],
        ))
    return dict(title=title, project_code=m.group(1) if m else None, status_date=_d(root.findtext(f"{NS}StatusDate")),
                start=_d(root.findtext(f"{NS}StartDate")), finish=_d(root.findtext(f"{NS}FinishDate")), tasks=tasks)
