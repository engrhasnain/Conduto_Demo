"""Builds the demo dataset: raw source files on disk + canonical database with lineage."""
import shutil
from collections import Counter

from sqlalchemy import select

from ..config import DATA_DIR, INBOX_DIR, SEED_VERSION, SOURCES_DIR, STATUS_PERIOD, UPLOADS_DIR
from ..db import Base, SessionLocal, engine
from ..i18n import ACTIVITY_NAMES, CIVIL_ACTIVITIES, COUNTRIES, PIPELINE_ACTIVITIES
from ..ml.train import train_models
from ..models import (Activity, BudgetLine, ChangeOrder, CostActual, Country, Document, DocumentChunk, ErpTransaction,
                      FxRate, Issue, MappingTemplate, Meta, Production, Progress, Project, ScheduleTask)
from .gp_writer import WINDOW_START, write_gp_export
from ..services.ask.schema_doc import VIEW_SQL
from ..services.ingestion.excel import parse_workbook
from ..services.ingestion.normalize import norm
from ..services.kpis import refresh_kpis
from .documents import T as DOC_TEXT
from .documents import (write_change_order, write_contract, write_final_report, write_monthly_report,
                        write_schedule_xml)
from .excel_writer import write_cost_workbook
from .fx import build_fx
from .inbox import build_inbox
from .simulate import simulate
from .specs import PROJECTS
from .templates import TEMPLATES

FILE_WORDS = {
    "es": dict(workbook="Control_Costos", schedule="Cronograma", contract="Contrato", report="Informe", closeout="Informe_Cierre"),
    "pt": dict(workbook="Controle_Custos", schedule="Cronograma", contract="Contrato", report="Relatorio", closeout="Relatorio_Encerramento"),
}
DOC_TITLES = {
    "es": dict(workbook="Control de costos", schedule="Cronograma (Microsoft Project)"),
    "pt": dict(workbook="Controle de custos", schedule="Cronograma (Microsoft Project)"),
}


def rel(path) -> str:
    return path.relative_to(DATA_DIR).as_posix()


def add_doc(db, project_id, doc_type, title, path, lang, pages_text=None, period=None, origin="seed") -> Document:
    d = Document(project_id=project_id, doc_type=doc_type, title=title, filename=path.name, rel_path=rel(path),
                 language=lang, pages=len(pages_text) if pages_text else None, period=period, origin=origin)
    db.add(d)
    db.flush()
    for i, text in enumerate(pages_text or [], start=1):
        db.add(DocumentChunk(document_id=d.id, page=i, text=text))
    return d


def is_seeded() -> bool:
    try:
        with SessionLocal() as db:
            m = db.get(Meta, "seed_version")
            return bool(m and m.value == SEED_VERSION)
    except Exception:
        return False


def seed(force: bool = False) -> bool:
    if not force and is_seeded():
        return False
    engine.dispose()
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP VIEW IF EXISTS v_project_overview")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql(VIEW_SQL)
    for d in (SOURCES_DIR, UPLOADS_DIR):
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True, exist_ok=True)
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    fx = build_fx()
    with SessionLocal() as db:
        for code, c in COUNTRIES.items():
            db.add(Country(code=code, name_es=c["es"], name_en=c["en"], name_pt=c["pt"], currency=c["currency"]))
        seen = {}
        for kind, acts in (("pipeline", PIPELINE_ACTIVITIES), ("civil", CIVIL_ACTIVITIES)):
            for code, *_ in acts:
                seen[code] = "both" if code in seen else kind
        for i, (code, kind) in enumerate(seen.items()):
            es, en, pt = ACTIVITY_NAMES[code]
            db.add(Activity(code=code, kind=kind, sort=i, name_es=es, name_en=en, name_pt=pt))
        db.add_all(FxRate(currency=cur, period=p, usd_per_unit=v) for (cur, p), v in fx.items())
        db.flush()

        fingerprints, usage = {}, Counter()
        seeded = [_seed_project(db, spec, fx, fingerprints, usage) for spec in PROJECTS]
        _seed_erp(db, seeded)

        for country, fp in fingerprints.items():
            tpl = TEMPLATES[country]
            db.add(MappingTemplate(
                name=tpl["name"], fingerprint=fp, doc_kind="cost_workbook", country_code=country,
                mapping={
                    "activities": {norm(label): code for code, label in tpl["labels"].items()},
                    "cost_types": {norm(v): k for k, v in tpl["cost_types"].items()},
                    "currency": COUNTRIES[country]["currency"],
                },
                times_used=usage[country] * 12,
            ))
        db.add(Meta(key="seed_version", value=SEED_VERSION))
        db.commit()
        build_inbox(fx)
        refresh_kpis(db)
        train_models(db)
    return True


def _seed_erp(db, seeded):
    """One Dynamics GP export per country with the last 12 months of the active projects."""
    by_country = {}
    for project, sim in seeded:
        if project.status == "active":
            by_country.setdefault(project.country_code, []).append((project, sim))
    erp_dir = SOURCES_DIR / "_ERP"
    erp_dir.mkdir(parents=True, exist_ok=True)
    for country, items in sorted(by_country.items()):
        lang = "pt" if country == "BR" else "es"
        path = erp_dir / f"GP_{country}_Transacciones_Proyectos_{WINDOW_START}_{STATUS_PERIOD}.xlsx"
        rows = write_gp_export(country, [s for _, s in items], path, lang)
        title = ("Dynamics GP – Transações de projetos" if lang == "pt" else "Dynamics GP – Transacciones de proyectos") + f" ({country})"
        doc = add_doc(db, None, "erp_export", title, path, lang, period=STATUS_PERIOD)
        ids = {p.code: p.id for p, _ in items}
        for r in rows:
            db.add(ErpTransaction(project_id=ids[r["project"]], period=r["period"], trx_date=r["trx_date"], journal=r["journal"],
                                  account=r["account"], cost_type=r["cost_type"], debit=r["debit"], credit=r["credit"],
                                  reference=r["reference"], source=r["source"], vendor=r["vendor"], document_id=doc.id,
                                  locator=r["locator"]))
    db.flush()


def _seed_project(db, spec, fx, fingerprints, usage):
    sim = simulate(spec, fx)
    code, lang, country = spec["code"], sim.lang, spec["country"]
    words, titles = FILE_WORDS[lang], DOC_TITLES[lang]
    pdir = SOURCES_DIR / code
    pdir.mkdir(parents=True, exist_ok=True)
    project = Project(
        code=code, name=spec["name"], country_code=country, client=spec["client"], kind=spec["kind"],
        status=spec["status"], contract_type=spec["contract_type"], terrain=spec["terrain"], region=spec["region"],
        diameter_in=spec.get("diameter"), length_km=spec.get("length"), currency=sim.currency,
        contract_value=sim.contract, bid_margin_pct=sim.bid_margin, start_period=spec["start"],
        planned_finish_period=sim.planned_finish, forecast_finish_period=sim.forecast_finish,
        manager=spec["manager"], description_es=spec["description"][0], description_en=spec["description"][1],
        description_pt=spec["description"][2], origin="seed",
    )
    db.add(project)
    db.flush()
    pid = project.id

    wb_path = pdir / f"{code}_{words['workbook']}.xlsx"
    loc = write_cost_workbook(sim, wb_path, country)
    wb_doc = add_doc(db, pid, "cost_workbook", f"{titles['workbook']} – {code}", wb_path, lang)
    parsed = parse_workbook(wb_path)  # the same parser the Ingest screen uses validates every seeded workbook
    wb_doc.checks = dict(ok=all(c["ok"] for c in parsed["checks"]), checks=parsed["checks"])
    fingerprints.setdefault(country, parsed["fingerprint"])
    usage[country] += 1
    project.bid_margin_document_id, project.bid_margin_locator = wb_doc.id, loc["bid_margin"]

    for a, cts in sim.budget_orig.items():
        for ct, amt in cts.items():
            db.add(BudgetLine(project_id=pid, activity_code=a, cost_type=ct, amount=amt, origin="original",
                              document_id=wb_doc.id, locator=loc["budget"][(a, ct)]))
    for a, cts in sim.costs.items():
        for ct, series in cts.items():
            for t, amt in enumerate(series):
                if amt:
                    db.add(CostActual(project_id=pid, period=sim.periods[t], activity_code=a, cost_type=ct, amount=amt,
                                      document_id=wb_doc.id, locator=loc["cost"][(a, ct, t)]))
    for a in sim.planned:
        for t, p in enumerate(sim.periods):
            db.add(Progress(project_id=pid, period=p, activity_code=a, planned_pct=round(sim.planned[a][t], 6),
                            actual_pct=round(sim.actual[a][t], 6), document_id=wb_doc.id, locator=loc["progress"][(a, t)]))
    for t, prod in enumerate(sim.production):
        db.add(Production(project_id=pid, period=prod["period"], km_welded_cum=prod["km"], welds_cum=prod["welds"],
                          weld_repairs_cum=prod["repairs"], document_id=wb_doc.id, locator=loc["production"][t]))

    xml_path = pdir / f"{code}_{words['schedule']}.xml"
    tlocs = write_schedule_xml(sim, xml_path)
    xml_doc = add_doc(db, pid, "schedule", f"{titles['schedule']} – {code}", xml_path, lang)
    for task in sim.tasks:
        db.add(ScheduleTask(project_id=pid, uid=task["uid"], name=TEMPLATES[country]["labels"][task["activity"]],
                            activity_code=task["activity"], baseline_start=task["baseline_start"],
                            baseline_finish=task["baseline_finish"], start=task["start"], finish=task["finish"],
                            pct_complete=task["pct"], document_id=xml_doc.id, locator=tlocs[task["uid"]]))

    L = DOC_TEXT[lang]
    c_path = pdir / f"{code}_{words['contract']}.pdf"
    pages, cloc = write_contract(sim, c_path)
    c_doc = add_doc(db, pid, "contract", f"{L['contract_label']} {code}-C", c_path, lang, pages)
    project.contract_document_id, project.contract_locator = c_doc.id, cloc

    for co in sim.cos:
        path = pdir / f"{code}_{co['number']}.pdf"
        pages, co_loc = write_change_order(sim, co, path)
        d = add_doc(db, pid, "change_order", f"{L['co_label']} {co['number']}", path, lang, pages, period=co["period"])
        db.add(ChangeOrder(project_id=pid, number=co["number"], title_es=co["titles"][0], title_en=co["titles"][1],
                           title_pt=co["titles"][2], cause=co["cause"], activity_code=co["activity"], amount=co["amount"],
                           status=co["status"], submitted_date=co["submitted_date"], decision_date=co["decision_date"],
                           schedule_impact_days=co["schedule_impact_days"], document_id=d.id, locator=co_loc))
        for ct, amt in co["budget_split"].items():
            db.add(BudgetLine(project_id=pid, activity_code=co["activity"], cost_type=ct, amount=amt,
                              origin="change_order", co_number=co["number"], document_id=d.id, locator=co_loc))

    report_periods = {i["period"] for i in sim.issues} | {c["period"] for c in sim.cos}
    if not sim.closed:
        report_periods.add(STATUS_PERIOD)
    issue_locs = {}
    for period in sorted(report_periods):
        t = sim.periods.index(period)
        path = pdir / f"{code}_{words['report']}_{period}.pdf"
        pages, ipages = write_monthly_report(sim, t, path, stale=spec.get("stale_report") == period)
        d = add_doc(db, pid, "progress_report", f"{L['report_label']} {period}", path, lang, pages, period=period)
        for idx, page in ipages.items():
            issue_locs[idx] = (d.id, page)
    if sim.closed:
        final_cost = sum(sum(s) for cts in sim.costs.values() for s in cts.values())
        revised = sim.contract + sum(c["amount"] for c in sim.cos if c["status"] == "approved")
        path = pdir / f"{code}_{words['closeout']}.pdf"
        pages = write_final_report(sim, path, final_cost, revised)
        add_doc(db, pid, "closeout_report", L["final_label"], path, lang, pages, period=sim.periods[-1])

    for idx, iss in enumerate(sim.issues):
        doc_id, page = issue_locs.get(idx, (None, None))
        db.add(Issue(project_id=pid, period=iss["period"], category=iss["category"], activity_code=iss["activity"],
                     days_lost=iss["days"], cost_impact=iss["cost"], description_es=iss["texts"][0],
                     description_en=iss["texts"][1], description_pt=iss["texts"][2], document_id=doc_id, locator=page))
    db.flush()
    return project, sim


if __name__ == "__main__":
    import time
    t0 = time.time()
    seed(force=True)
    with SessionLocal() as db:
        n = {m.__tablename__: db.query(m).count() for m in (Project, Document, CostActual, Progress, ChangeOrder, Issue, DocumentChunk)}
    print(f"Seeded in {time.time() - t0:.1f}s: {n}")
