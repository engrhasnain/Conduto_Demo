import pytest


def test_health(client):
    r = client.get("/api/health").json()
    assert r["status"] == "ok"
    assert r["projects"] == 18
    assert r["ai_enabled"] is False


def test_portfolio(client):
    r = client.get("/api/portfolio").json()
    assert r["summary"]["active_count"] == 6
    worst = next(i for i in r["insights"] if i["code"] == "worst_project")
    assert worst["project"] == "EC-2503"
    p = next(x for x in r["projects"] if x["code"] == "EC-2503")
    assert p["health"] == "red"
    assert "COST_OVERRUN" in p["flags"] and "PENDING_CO" in p["flags"]


def test_project_waterfall_reconciles(client):
    d = client.get("/api/projects/EC-2503").json()
    steps = d["waterfall"]["steps"]
    assert steps[0]["key"] == "bid_margin" and steps[-1]["key"] == "forecast_margin"
    assert abs(sum(s["value"] for s in steps[:-1]) - steps[-1]["value"]) < 1.0
    k = d["kpis"]
    assert abs(k["forecast_margin_pct"] - 0.045) < 0.002
    assert len([c for c in d["change_orders"] if c["status"] == "pending"]) == 3
    assert d["drivers"] and d["scurve"] and d["schedule"] and d["issues"]


def test_lineage_points_at_real_cell(client):
    lin = client.get("/api/projects/EC-2503/lineage/CRU").json()
    cost = lin["costs"][0]
    prev = client.get("/api/lineage", params={"document_id": cost["document_id"], "locator": cost["locator"]}).json()
    assert prev["type"] == "sheet"
    assert prev["value"] == cost["amount"]
    target = [c for row in prev["grid"] for c in row["cells"] if c["target"]]
    assert len(target) == 1


def test_pdf_lineage_and_file(client):
    d = client.get("/api/projects/EC-2503").json()
    co = next(c for c in d["change_orders"] if c["number"] == "OC-007")
    prev = client.get("/api/lineage", params={"document_id": co["document_id"], "locator": co["locator"]}).json()
    assert prev["type"] == "pdf" and "OC-007" in prev["text"]
    f = client.get(f"/api/documents/{co['document_id']}/file")
    assert f.status_code == 200 and f.headers["content-type"] == "application/pdf"


def test_benchmarks_and_estimate(client):
    b = client.get("/api/benchmarks").json()
    assert set(b["by_terrain"]) == {"coast", "highlands", "rainforest"}
    assert b["by_terrain"]["rainforest"]["cost_per_km_p50"] > b["by_terrain"]["coast"]["cost_per_km_p50"]
    e = client.post("/api/benchmarks/estimate", json=dict(terrain="rainforest", diameter_in=16, length_km=50, target_margin=0.15)).json()
    assert e["cost_p25"] < e["cost_p50"] < e["cost_p75"] < e["suggested_price"]


@pytest.mark.parametrize("lang", ["es", "en", "pt"])
def test_ask_local_suggestions(client, lang):
    sugg = client.get("/api/ask/suggestions", params={"lang": lang}).json()["suggestions"]
    assert len(sugg) == 10
    for s in sugg:
        r = client.post("/api/ask", json=dict(question=s["text"], lang=lang)).json()
        assert r["engine"] == "local", s
        assert len(r["answer"]) > 40, s
        assert r["trace"][0]["tool"] == "intent"


@pytest.mark.parametrize("question,lang,intent,entity", [
    ("¿Cómo va el Tramo B?", "es", "project_status", ("project", "EC-2503")),
    ("Which projects are behind schedule in Peru?", "en", "delays", ("countries", ["PE"])),
    ("Quanto temos em ordens pendentes no Brasil?", "pt", "pending_cos", ("countries", ["BR"])),
    ("¿cuántos días perdimos por lluvias?", "es", "lost_days", ("category", "weather")),
    ("lessons learned in the highlands", "en", "lessons", ("terrain", "highlands")),
    ("¿qué dice el contrato de PE-2410 sobre multas?", "es", "contract", ("project", "PE-2410")),
])
def test_ask_free_form_offline(client, question, lang, intent, entity):
    r = client.post("/api/ask", json=dict(question=question, lang=lang)).json()
    t = r["trace"][0]
    assert t["intent"] == intent
    assert t["entities"][entity[0]] == entity[1]
    assert any(s["tool"] in ("run_sql", "search_documents", "service") for s in r["trace"][1:])


def test_ask_conversation_memory(client):
    first = client.post("/api/ask", json=dict(question="¿Cómo va el Tramo B?", lang="es")).json()
    assert first["context"]["entities"]["project"] == "EC-2503" and first["followups"]
    second = client.post("/api/ask", json=dict(question="¿y por qué cayó el margen?", lang="es", context=first["context"])).json()
    assert second["intent"] == "margin_project" and second["context"]["entities"]["project"] == "EC-2503"
    third = client.post("/api/ask", json=dict(question="Which projects are behind schedule?", lang="en")).json()
    fourth = client.post("/api/ask", json=dict(question="and in Brazil?", lang="en", context=third["context"])).json()
    assert fourth["intent"] == "delays" and fourth["context"]["entities"]["countries"] == ["BR"]


@pytest.mark.parametrize("question,lang,faq_id", [
    ("¿qué es una orden de cambio?", "es", "change_order"), ("what is earned value?", "en", "earned_value"),
    ("o que é eficiência de custo?", "pt", "cost_efficiency"), ("hola", "es", "greeting"), ("is this real data?", "en", "real_data"),
])
def test_ask_general_questions(client, question, lang, faq_id):
    r = client.post("/api/ask", json=dict(question=question, lang=lang)).json()
    kb = [s for s in r["trace"] if s["tool"] == "knowledge_base"]
    assert kb and kb[0]["purpose"] == faq_id


def test_ask_out_of_scope_is_honest(client):
    r = client.post("/api/ask", json=dict(question="¿cuál es la capital de Francia?", lang="es")).json()
    assert "servicios externos" in r["answer"] and "Claude" in r["answer"] and r["suggestions"]


def test_ask_never_dead_ends(client):
    r = client.post("/api/ask", json=dict(question="zxqv blorp", lang="es")).json()
    assert r["answer"] and r["suggestions"]


def test_sql_guard():
    from app.services.ask.sql_guard import SqlError, run_readonly
    assert run_readonly("SELECT count(*) FROM projects")["rows"][0][0] >= 18
    for bad in ("DELETE FROM projects", "SELECT 1; DROP TABLE projects", "PRAGMA table_info(projects)", "UPDATE projects SET name='x'"):
        with pytest.raises(SqlError):
            run_readonly(bad)


def test_ingest_seed_workbook_recognized_and_idempotent(client, tmp_path):
    from app.config import SOURCES_DIR
    before = client.get("/api/projects/BR-2501").json()["kpis"]
    path = SOURCES_DIR / "BR-2501" / "BR-2501_Controle_Custos.xlsx"
    with open(path, "rb") as fh:
        job = client.post("/api/ingest/upload", files={"file": (path.name, fh, "application/octet-stream")}).json()
    pv = job["preview"]
    assert pv["kind"] == "cost_workbook" and pv["engine"] == "template"
    assert pv["project"]["code"] == "BR-2501"
    assert all(c["ok"] for c in pv["checks"]), pv["checks"]
    res = client.post(f"/api/ingest/jobs/{job['id']}/confirm", json={}).json()["result"]
    assert res["template"]["created"] is False
    after = client.get("/api/projects/BR-2501").json()["kpis"]
    assert abs(after["eac"] - before["eac"]) / before["eac"] < 1e-6


def test_ingest_legacy_workbook_creates_historical_project(client):
    n_before = len(client.get("/api/benchmarks").json()["points"])
    job = client.post("/api/ingest/samples/Historico_Linea_Flujo_Tiputini_2019.xlsx").json()
    pv = job["preview"]
    assert pv["kind"] == "legacy_workbook"
    assert pv["new_project"]["terrain"] == "rainforest"
    assert pv["new_project"]["contract_value"] == 12_480_000
    assert all(c["ok"] for c in pv["checks"]), pv["checks"]
    combined = next(m for m in pv["row_mapping"] if m["label"] == "Sold. + END")
    assert combined["code"] == "SOL" and combined["confidence"] < 0.8
    res = client.post(f"/api/ingest/jobs/{job['id']}/confirm", json={}).json()["result"]
    assert res["created"] and res["template"]["created"]
    assert len(client.get("/api/benchmarks").json()["points"]) == n_before + 1
    # the saved template is recognized the second time
    job2 = client.post("/api/ingest/samples/Historico_Linea_Flujo_Tiputini_2019.xlsx").json()
    assert job2["preview"]["engine"] == "template"


def test_ingest_change_order_pdf(client):
    before = client.get("/api/projects/EC-2503").json()["kpis"]["pending_co_value"]
    job = client.post("/api/ingest/samples/EC-2503_OC-012_Variante_km48.pdf").json()
    pv = job["preview"]
    fields = {f["field"]: f["value"] for f in pv["fields"]}
    assert pv["kind"] == "change_order_pdf"
    grounded = {f["field"]: f["grounded"] for f in pv["fields"] if f["grounded"] is not None}
    assert grounded and all(grounded.values()), grounded
    assert fields["co_number"] == "OC-012" and fields["status"] == "pending" and fields["currency"] == "USD"
    assert fields["activity_code"] == "DDV" and fields["cause"] == "geotech"
    res = client.post(f"/api/ingest/jobs/{job['id']}/confirm", json={}).json()["result"]
    assert res["after"]["pending_co_usd"] > res["before"]["pending_co_usd"]
    after = client.get("/api/projects/EC-2503").json()["kpis"]["pending_co_value"]
    assert abs(after - before - fields["amount"]) < 1.0


def test_ingest_schedule_xml(client):
    job = client.post("/api/ingest/samples/PE-2410_Cronograma_rev5.xml").json()
    pv = job["preview"]
    assert pv["project"]["code"] == "PE-2410" and pv["changes"]
    assert pv["forecast_finish"]["new"] > pv["forecast_finish"]["old"]
    res = client.post(f"/api/ingest/jobs/{job['id']}/confirm", json={}).json()["result"]
    assert res["after"]["delay_months"] == res["before"]["delay_months"] + 2


def test_scanned_pdf_is_triaged_not_misread(client):
    job = client.post("/api/ingest/samples/EC-2503_OC-013_escaneada.pdf").json()
    assert job["status"] == "needs_ai"
    pv = job["preview"]
    assert pv["kind"] == "scanned_pdf" and pv["content_state"] == "scanned" and pv["ready"] is False
    assert pv["ocr_estimate_usd"][1] > 0


def test_datahub_quality_checks(client):
    h = client.get("/api/datahub").json()
    q = h["quality"]
    assert q["lineage"]["rate"] == 1.0
    assert q["workbook_totals"]["passed"] == q["workbook_totals"]["checked"] >= 18
    assert [(m["project"], m["period"]) for m in q["report_vs_workbook"]["mismatches"]] == [("EC-2503", "2026-04")]
    kinds = sorted(d["kind"] for d in q["erp_vs_excel"]["discrepancies"])
    assert kinds == ["duplicate", "missing_in_erp", "missing_in_excel"]
    unexplained = {(a["project"], a["period"]) for a in h["anomalies"]["items"] if not a["explanation"]}
    assert {("BR-2501", "2026-06"), ("PE-2410", "2025-11")} <= unexplained
    assert h["models"]["label_mapper"]["accuracy"] >= 0.9
    assert h["models"]["intent_classifier"]["accuracy"] >= 0.85


def test_drilldown_lists_match_the_totals(client):
    """The lists behind clickable numbers add up to the numbers themselves."""
    pf = client.get("/api/portfolio").json()
    cos = client.get("/api/change_orders?status=pending").json()
    assert len(cos) == pf["summary"]["pending_co_count"]
    assert sum(c["amount_usd"] for c in cos) == pytest.approx(pf["summary"]["pending_co_usd"], rel=1e-6)
    assert all(c["days_pending"] is not None and c["document_id"] for c in cos)
    assert {c["country"] for c in client.get("/api/change_orders?status=pending&country=pe").json()} <= {"PE"}

    hub = client.get("/api/datahub").json()
    assert len(client.get("/api/documents").json()) == hub["files"]["total"]
    wb = client.get("/api/documents?doc_type=cost_workbook,legacy_workbook").json()
    assert len(wb) == hub["files"]["by_type"].get("cost_workbook", 0) + hub["files"]["by_type"].get("legacy_workbook", 0)
    one = client.get("/api/documents?project=ec-2503&doc_type=change_order").json()
    assert one and {d["project"] for d in one} == {"EC-2503"}
    q = hub["quality"]
    assert len(q["workbook_totals"]["items"]) == q["workbook_totals"]["checked"]
    assert len(q["report_vs_workbook"]["items"]) == q["report_vs_workbook"]["checked"]


def test_project_has_anomalies_and_erp(client):
    d = client.get("/api/projects/EC-2503").json()
    assert d["anomalies"] and all(a["explanation"] for a in d["anomalies"])
    assert [x["kind"] for x in d["erp"]["discrepancies"]] == ["missing_in_excel"]


def test_export_consolidated(client):
    r = client.get("/api/export/consolidated.xlsx")
    assert r.status_code == 200 and r.content[:2] == b"PK"


def test_reset(client):
    assert client.post("/api/admin/reset").json()["status"] == "reset"
    assert client.get("/api/health").json()["projects"] == 18
