"""PDF extraction: text via pypdf, fields via regex rules or Claude (structured output),
then a groundedness check: a field counts as verified only if its value appears
verbatim in the document. Scans without a text layer are detected and triaged to OCR."""
import base64
import re

from pypdf import PdfReader

from ...config import ai_enabled
from ...fmt import fmt_number
from ...i18n import ACTIVITY_NAMES, CO_CAUSES, CO_STATUS
from ...seed.templates import TEMPLATES
from ..llm import LLMError, extract_json
from .mapping import map_activity
from .normalize import norm, parse_number

OCR_COST_PER_PAGE_USD = (0.01, 0.03)  # rough range for a vision model reading one page

PROJECT_CODE_RE = re.compile(r"\b([A-Z]{2}-\d{4})\b")
CO_FIELDS = ["doc_type", "project_code", "co_number", "title", "title_en", "amount", "currency", "submitted_date",
             "status", "cause", "activity_code", "schedule_impact_days", "work_already_executed"]


def read_pdf(path) -> list[str]:
    reader = PdfReader(str(path))
    return [(p.extract_text() or "") for p in reader.pages]


def content_state(path, pages: list[str]) -> str:
    """text | scanned (page images, no text layer) | empty."""
    if sum(len(p.strip()) for p in pages) >= 40:
        return "text"
    reader = PdfReader(str(path))
    has_images = any(len(pg.images) for pg in reader.pages)
    return "scanned" if has_images else "empty"


def grounded(fields: dict, pages: list[str]) -> dict:
    """Which extracted values can be found verbatim in the document text."""
    flat = re.sub(r"\s+", " ", "\n".join(pages))
    nflat = norm(flat)
    out = {}
    for f, v in fields.items():
        if v in (None, "", 0) or f in ("doc_type", "work_already_executed", "title_en"):
            continue
        if f == "amount":
            ok = any(c in flat for c in (fmt_number(float(v), "es"), fmt_number(float(v), "en"), f"{float(v):.0f}"))
        elif f == "submitted_date":
            y, m, d = str(v).split("-")
            ok = f"{d}/{m}/{y}" in flat or str(v) in flat
        elif f == "schedule_impact_days":
            ok = re.search(rf"\b{int(v)}\s*d[ií]as", flat) is not None
        elif f == "currency":
            ok = {"USD": "USD", "PEN": "S/", "BRL": "R$"}.get(v, v) in flat
        elif f == "cause":
            ok = any(norm(n) in nflat for n in CO_CAUSES.get(v, ()))
        elif f == "status":
            ok = any(norm(n) in nflat for n in CO_STATUS.get(v, ()))
        elif f == "activity_code":
            names = list(ACTIVITY_NAMES.get(v, ())) + [t["labels"].get(v, "") for t in TEMPLATES.values()]
            ok = any(n and norm(n) in nflat for n in names)
        elif f == "title":
            ok = norm(str(v))[:40] in nflat
        else:
            ok = norm(str(v)) in nflat
        out[f] = ok
    return out


def classify(text: str) -> str:
    t = norm(text)
    if "orden de cambio" in t or "ordem de alteracao" in t or "change order" in t:
        return "change_order"
    if "contrato de constru" in t or "construction contract" in t:
        return "contract"
    if "informe de cierre" in t or "relatorio de encerramento" in t:
        return "closeout_report"
    if "informe mensual" in t or "relatorio mensal" in t or "monthly progress" in t:
        return "progress_report"
    return "other"


def _after(text: str, labels: list[str], pattern: str = r"(.+)") -> str | None:
    for lab in labels:
        m = re.search(rf"{lab}\s*:?\s*{pattern}", text, re.I)
        if m:
            return m.group(1).strip()
    return None


def rules_extract(pages: list[str]) -> dict:
    text = "\n".join(pages)
    out = {"doc_type": classify(text)}
    m = re.search(r"(?:ORDEN DE CAMBIO|ORDEM DE ALTERA\S+)\s*N\S?\s*([A-Z]{2}-\d{3})", text, re.I)
    out["co_number"] = m.group(1) if m else None
    m = PROJECT_CODE_RE.search(text)
    out["project_code"] = m.group(1) if m else None
    m = re.search(r"(?:Monto solicitado|Valor solicitado|Amount requested)\s*:?\s*(USD|S/|R\$)\s*([\d.,]+)", text, re.I)
    if m:
        out["currency"] = {"USD": "USD", "S/": "PEN", "R$": "BRL"}[m.group(1)]
        out["amount"] = parse_number(m.group(2))
    d = _after(text, ["Fecha de presentaci\\S+", "Data de apresenta\\S+"], r"(\d{2}/\d{2}/\d{4})")
    if d:
        dd, mm, yy = d.split("/")
        out["submitted_date"] = f"{yy}-{mm}-{dd}"
    st = _after(text, ["Estado", "Situa\\S+"], r"([A-Za-zÀ-ÿ ]+)")
    if st:
        n = norm(st)
        out["status"] = "pending" if n.startswith("pend") else "approved" if n.startswith("aprob") or n.startswith("aprov") else "rejected" if n.startswith("rech") or n.startswith("rejei") else None
    act = _after(text, ["Actividad afectada", "Atividade afetada"])
    if act:
        out["activity_label"] = act.split("\n")[0]
        out["activity_code"] = map_activity(out["activity_label"])["code"]
    cause = _after(text, ["Causa"])
    if cause:
        nc = norm(cause.split("\n")[0])
        for key, names in CO_CAUSES.items():
            if any(norm(nm) == nc for nm in names):
                out["cause"] = key
    days = _after(text, ["Impacto en plazo", "Impacto no prazo"], r"(\d+)")
    out["schedule_impact_days"] = int(days) if days else None
    m = re.search(r"(?:Descripci\S+n|Descri\S+o)\s*\n(.+?)\n\s*(?:Justificaci\S+n|Justificativa)", text, re.S | re.I)
    out["title"] = re.sub(r"\s+", " ", m.group(1)).strip().rstrip(".") if m else None
    out["work_already_executed"] = bool(re.search(r"ejecutados en campo|executados em campo", text, re.I))
    return out


def _co_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "doc_type": {"type": "string", "enum": ["change_order", "contract", "progress_report", "closeout_report", "other"]},
            "project_code": {"type": "string", "description": "Project code like EC-2503, or empty"},
            "co_number": {"type": "string", "description": "Change order number like OC-012, or empty"},
            "title": {"type": "string", "description": "One-line description in the document's language"},
            "title_en": {"type": "string", "description": "The same description translated to English"},
            "amount": {"type": "number", "description": "Amount requested, 0 if none"},
            "currency": {"type": "string", "enum": ["USD", "PEN", "BRL", ""]},
            "submitted_date": {"type": "string", "description": "YYYY-MM-DD or empty"},
            "status": {"type": "string", "enum": ["approved", "pending", "rejected", ""]},
            "cause": {"type": "string", "enum": list(CO_CAUSES) + [""]},
            "activity_code": {"type": "string", "enum": list(ACTIVITY_NAMES) + [""]},
            "schedule_impact_days": {"type": "integer"},
            "work_already_executed": {"type": "boolean", "description": "True if the text says the work was already executed before approval"},
            "confidence": {
                "type": "object",
                "properties": {f: {"type": "number"} for f in CO_FIELDS},
                "required": CO_FIELDS,
                "additionalProperties": False,
            },
        },
        "required": CO_FIELDS + ["confidence"],
        "additionalProperties": False,
    }


def ai_extract(pages: list[str]) -> dict:
    schema = _co_schema()
    acts = "; ".join(f"{c} = {n[0]} / {n[1]}" for c, n in ACTIVITY_NAMES.items())
    system = (
        "You extract structured data from construction project documents (Spanish or Portuguese) for a pipeline "
        "contractor. Use empty strings or 0 for fields that are not present; never guess. For each field give a "
        "confidence between 0 and 1. Canonical activity codes: " + acts + "."
    )
    text = "\n\n".join(f"--- page {i} ---\n{p}" for i, p in enumerate(pages, start=1))
    return extract_json(system, text[:60_000], schema)


def ai_extract_scan(path) -> dict:
    """Vision OCR + extraction for scanned PDFs (only called when an API key is configured)."""
    data = base64.standard_b64encode(open(path, "rb").read()).decode()
    content = [
        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data}},
        {"type": "text", "text": "Extract the change-order fields from this scanned document."},
    ]
    schema = _co_schema()
    system = ("You extract structured data from scanned construction documents (Spanish or Portuguese). Use empty strings "
              "or 0 for fields you cannot read; never guess. Give a confidence between 0 and 1 for each field.")
    return extract_json(system, content, schema)


def extract(pages: list[str]) -> tuple[dict, dict, str]:
    """Returns (fields, confidence, engine)."""
    rules = rules_extract(pages)
    if ai_enabled():
        try:
            ai = ai_extract(pages)
            conf = ai.pop("confidence", {})
            merged = {}
            for f in CO_FIELDS:
                v = ai.get(f)
                merged[f] = v if v not in ("", None, 0) or f in ("work_already_executed",) else rules.get(f)
                if rules.get(f) not in (None, "") and merged[f] == rules.get(f):
                    conf[f] = max(conf.get(f, 0), 0.97)  # two independent methods agree
            return merged, conf, "ai"
        except LLMError:
            pass
    conf = {f: (0.9 if rules.get(f) not in (None, "") else 0.0) for f in CO_FIELDS}
    rules.setdefault("title_en", None)
    return {f: rules.get(f) for f in CO_FIELDS}, conf, "rules"
