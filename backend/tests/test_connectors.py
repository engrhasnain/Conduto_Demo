"""Connectors and the bid pipeline they feed."""


def test_connector_catalog(client):
    d = client.get("/api/connectors").json()
    by_key = {c["key"]: c for c in d["connectors"]}
    assert {"files", "dynamics_gp", "sales", "sap", "d365_finance", "power_bi"} <= set(by_key)
    assert d["summary"]["connected"] == 3
    for key in ("files", "dynamics_gp", "sales"):
        assert by_key[key]["status"] == "connected" and by_key[key]["last_run"] and by_key[key]["records"] > 0
    assert by_key["sap"]["last_run"] is None and by_key["sap"]["status"] == "available"
    assert all(set(c["summary"]) == {"es", "en", "pt"} and c["mapping"] for c in d["connectors"])


def test_bid_check_flags_underpriced_bids(client):
    p = client.get("/api/bids").json()
    risk = {b["crm_id"]: b["check"]["risk"] for b in p["bids"] if b.get("check")}
    assert risk["OPP-2026-014"] == "red"  # same client and terrain as EC-2503, priced below history
    assert risk["OPP-2026-019"] == "amber"
    assert risk["OPP-2026-030"] == "none"  # civil works: no comparable history yet
    won = {b["project_code"] for b in p["bids"] if b["stage"] == "won"}
    active = {x["code"] for x in client.get("/api/portfolio").json()["projects"] if x["status"] == "active"}
    assert won == active  # every active project traces back to the bid that won it
    d = client.get("/api/bids/OPP-2026-014").json()
    assert d["comparables"] and d["document_id"] and d["locator"].startswith("Oportunidades!L")
    assert client.get("/api/lineage", params=dict(document_id=d["document_id"], locator=d["locator"])).status_code == 200
    assert client.get("/api/bids/OPP-0000-000").status_code == 404


def test_sales_sync_reads_changes_and_the_check_reacts(client):
    r = client.post("/api/connectors/sales/sync").json()
    assert (r["read"], r["new"], r["updated"]) == (17, 1, 1)
    assert {c["crm_id"]: c["kind"] for c in r["details"]["changes"]} == {"OPP-2026-019": "updated", "OPP-2026-035": "new"}
    b19 = next(b for b in client.get("/api/bids").json()["bids"] if b["crm_id"] == "OPP-2026-019")
    assert b19["stage"] == "negotiation" and b19["check"]["risk"] == "red"  # renegotiated 6% lower
    again = client.post("/api/connectors/sales/sync").json()
    assert (again["new"], again["updated"]) == (0, 0)
    assert client.get("/api/connectors/sales").json()["runs"][0]["trigger"] == "manual"


def test_other_syncs_and_guards(client):
    f = client.post("/api/connectors/files/sync").json()
    assert f["issues"] == len(f["details"]["waiting"]) and f["read"] > 100
    g = client.post("/api/connectors/dynamics_gp/sync").json()
    assert g["issues"] == 3 and g["status"] == "attention"
    assert client.post("/api/connectors/sap/sync").status_code == 409
    assert client.post("/api/connectors/unknown/sync").status_code == 404
    assert client.post("/api/connectors/sales/test").json()["ok"]


def test_ask_about_bids_and_connectors(client):
    r = client.post("/api/ask", json=dict(question="Which bids are priced below history?", lang="en")).json()
    assert r["intent"] == "bids" and "OPP-2026-014" in r["answer"]
    r = client.post("/api/ask", json=dict(question="¿qué son los conectores?", lang="es")).json()
    assert "solo lectura" in r["answer"]
