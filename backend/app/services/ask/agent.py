"""Natural-language Q&A over the consolidated data.

Claude plans the answer and calls two tools: `run_sql` (read-only, for every number)
and `search_documents` (BM25 over contracts, change orders and reports, for context).
The response carries the full trace so the UI can show exactly how an answer was built."""
import json
import re

import anthropic
from sqlalchemy.orm import Session

from ...config import ANTHROPIC_EFFORT
from ...models import Document
from ..llm import LLMError, create
from ..search import INDEX
from .schema_doc import SCHEMA_DOC
from .sql_guard import SqlError, run_readonly

LANG_NAME = {"es": "Spanish", "en": "English", "pt": "Portuguese (Brazil)"}
MAX_STEPS = 8

SYSTEM = f"""You are the project-controls analyst for Conduto, a pipeline and civil-works contractor operating in
Ecuador, Peru and Brazil. You answer questions from executives and project managers using the consolidated project
database and the source documents (contracts, change orders, monthly and close-out reports).

How to work:
- Use run_sql for anything numeric. Let SQL do the aggregation; never invent or estimate figures.
- Use search_documents for qualitative context: causes, contract clauses, events, lessons learned. Documents are
  written in Spanish or Portuguese; search with words in those languages.
- Compare projects in USD (*_usd columns). For a single project you may also quote its own currency.
- Percentages with one decimal (4.5%); margin erosion in percentage points. Money as USD 3.4M / USD 850k.
- Cite documents inline as [doc:<document_id> p.<page>] right after the fact they support. Mention project codes
  (e.g. EC-2503) so the UI can link them.
- Lead with the direct answer in one or two sentences, then supporting bullets or a small markdown table.
  No preamble, no restating the question.
- If the data cannot answer the question, say so and name the data that would be needed.
- This is a synthetic demonstration dataset; never make up projects, documents or numbers.
- Write for business readers: avoid abbreviations and jargon. Say "cost efficiency" (not CPI), "schedule efficiency"
  (not SPI), "estimated cost at completion" (not EAC), "change orders" (not COs/OC), "accounting system" (not ERP/GP).
- General questions (concepts, how this system works, small talk, or topics unrelated to the data) are welcome:
  answer them briefly and helpfully without tools, and say when something is outside Conduto's project data.

<database_schema>
{SCHEMA_DOC}
</database_schema>"""

TOOLS = [
    {
        "name": "run_sql",
        "description": "Run one read-only SQLite SELECT (or WITH ... SELECT) against the project-controls database. Returns columns and up to 200 rows.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "A single SELECT statement."},
                "purpose": {"type": "string", "description": "Short description of what this query answers, shown to the user."},
            },
            "required": ["query", "purpose"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_documents",
        "description": "Keyword search over source documents (contracts, change orders, monthly and close-out reports). Returns the best-matching pages with document_id, page and a snippet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keywords, ideally in Spanish or Portuguese."},
                "project_code": {"type": "string", "description": "Optional project code filter, e.g. EC-2503. Empty string for all projects."},
            },
            "required": ["query", "project_code"],
            "additionalProperties": False,
        },
    },
]
TOOLS[-1]["cache_control"] = {"type": "ephemeral"}

CITE_RE = re.compile(r"\[doc:(\d+)(?:\s*p\.(\d+))?\]")
SRC_RE = re.compile(r"\[src:(\d+)\|([^\]]+)\]")  # exact cell / row, e.g. [src:12|Costos mensuales!F23]


def _run_tool(db: Session, name: str, args: dict, trace: list) -> tuple[str, bool]:
    if name == "run_sql":
        query = args.get("query", "")
        try:
            res = run_readonly(query)
        except SqlError as e:
            trace.append(dict(tool="run_sql", purpose=args.get("purpose", ""), query=query, error=str(e)))
            return f"SQL error: {e}", True
        trace.append(dict(tool="run_sql", purpose=args.get("purpose", ""), query=query, columns=res["columns"],
                          rows=res["rows"][:50], row_count=len(res["rows"]), truncated=res["truncated"]))
        return json.dumps(res, default=str), False
    if name == "search_documents":
        hits = INDEX.search(db, args.get("query", ""), project_code=args.get("project_code") or None)
        trace.append(dict(tool="search_documents", query=args.get("query", ""), project_code=args.get("project_code") or None,
                          hits=[{k: h[k] for k in ("document_id", "title", "project_code", "page")} for h in hits]))
        return json.dumps(hits, default=str), False
    return f"Unknown tool {name}", True


def ask(db: Session, question: str, lang: str, history: list[dict] | None = None) -> dict:
    messages = []
    for turn in (history or [])[-6:]:
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": f"{question}\n\n(Respond in {LANG_NAME.get(lang, 'English')}.)"})
    trace: list[dict] = []
    answer = ""
    for _ in range(MAX_STEPS):
        try:
            resp = create(
                max_tokens=16000,
                system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
                tools=TOOLS,
                messages=messages,
                output_config={"effort": ANTHROPIC_EFFORT},
            )
        except anthropic.APIConnectionError as e:
            raise LLMError(f"Cannot reach the Claude API: {e}") from e
        except anthropic.RateLimitError as e:
            raise LLMError("Claude API rate limit reached, try again shortly.") from e
        except anthropic.APIStatusError as e:
            raise LLMError(f"Claude API error {e.status_code}: {e.message}") from e
        messages.append({"role": "assistant", "content": resp.content})
        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if resp.stop_reason != "tool_use" or not tool_uses:
            answer = "\n".join(b.text for b in resp.content if b.type == "text").strip()
            break
        results = []
        for tu in tool_uses:
            content, is_error = _run_tool(db, tu.name, tu.input if isinstance(tu.input, dict) else {}, trace)
            results.append({"type": "tool_result", "tool_use_id": tu.id, "content": content, "is_error": is_error})
        messages.append({"role": "user", "content": results})
    else:
        answer = answer or "I could not finish the analysis within the step budget. Try a narrower question."
    return dict(answer=answer, citations=citations(db, answer), trace=trace, engine="claude")


def citations(db: Session, answer: str) -> list[dict]:
    out, seen = [], set()
    found = [(int(m.group(1)), f"p.{m.group(2) or 1}") for m in CITE_RE.finditer(answer)]
    found += [(int(m.group(1)), m.group(2)) for m in SRC_RE.finditer(answer)]
    for doc_id, locator in found:
        if (doc_id, locator) in seen:
            continue
        seen.add((doc_id, locator))
        d = db.get(Document, doc_id)
        if d:
            page = int(locator[2:]) if locator.startswith("p.") and locator[2:].isdigit() else None
            out.append(dict(document_id=doc_id, page=page, locator=locator, title=d.title, filename=d.filename))
    return out
