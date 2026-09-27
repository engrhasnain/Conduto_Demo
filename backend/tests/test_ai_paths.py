"""AI code paths with Claude mocked out: agent tool loop, citation parsing, and
the AI-vs-rules merge for PDF extraction."""
from types import SimpleNamespace as NS


def _resp(blocks, stop):
    return NS(content=blocks, stop_reason=stop)


def test_agent_tool_loop(client, monkeypatch):
    from app.db import SessionLocal
    from app.services.ask import agent

    calls = []

    def fake_create(**params):
        calls.append(params)
        if len(calls) == 1:
            return _resp([
                NS(type="text", text="Checking."),
                NS(type="tool_use", id="t1", name="run_sql", input={"query": "SELECT code, forecast_margin_pct FROM v_project_overview WHERE code='EC-2503'", "purpose": "margin"}),
                NS(type="tool_use", id="t2", name="search_documents", input={"query": "orden de cambio cruces", "project_code": "EC-2503"}),
            ], "tool_use")
        # second turn: the tool results must be sent back in one user message
        results = params["messages"][-1]["content"]
        assert [r["tool_use_id"] for r in results] == ["t1", "t2"]
        assert all(not r["is_error"] for r in results)
        return _resp([NS(type="text", text="EC-2503 forecast margin is 4.5% [doc:1 p.1].")], "end_turn")

    monkeypatch.setattr(agent, "create", fake_create)
    with SessionLocal() as db:
        out = agent.ask(db, "margin?", "en")
    assert out["answer"].startswith("EC-2503")
    assert [t["tool"] for t in out["trace"]] == ["run_sql", "search_documents"]
    assert out["trace"][0]["rows"][0][0] == "EC-2503"
    assert out["citations"] and out["citations"][0]["document_id"] == 1
    assert "Respond in English" in calls[0]["messages"][0]["content"]


def test_agent_reports_sql_errors_to_model(client, monkeypatch):
    from app.db import SessionLocal
    from app.services.ask import agent

    state = {"n": 0}

    def fake_create(**params):
        state["n"] += 1
        if state["n"] == 1:
            return _resp([NS(type="tool_use", id="x", name="run_sql", input={"query": "DELETE FROM projects", "purpose": "bad"})], "tool_use")
        res = params["messages"][-1]["content"][0]
        assert res["is_error"] is True
        return _resp([NS(type="text", text="Cannot do that.")], "end_turn")

    monkeypatch.setattr(agent, "create", fake_create)
    with SessionLocal() as db:
        out = agent.ask(db, "delete everything", "en")
    assert out["trace"][0]["error"]


def test_pdf_ai_merge(monkeypatch):
    from app.config import INBOX_DIR
    from app.services.ingestion import pdf

    pages = pdf.read_pdf(INBOX_DIR / "EC-2503_OC-012_Variante_km48.pdf")
    rules = pdf.rules_extract(pages)

    def fake_ai(_pages):
        d = {f: rules.get(f) for f in pdf.CO_FIELDS}
        d.update(title_en="Route variant km 48", schedule_impact_days=20, confidence={f: 0.8 for f in pdf.CO_FIELDS})
        return d

    monkeypatch.setattr(pdf, "ai_enabled", lambda: True)
    monkeypatch.setattr(pdf, "ai_extract", fake_ai)
    fields, conf, engine = pdf.extract(pages)
    assert engine == "ai"
    assert fields["co_number"] == "OC-012" and fields["title_en"] == "Route variant km 48"
    assert conf["co_number"] >= 0.97  # AI and rules agree
