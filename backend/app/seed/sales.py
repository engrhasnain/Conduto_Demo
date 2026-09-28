"""Synthetic sales-system data (Dynamics 365 Sales opportunities) and the connectors' run history.

Two states are written on purpose:
- the database holds what the connector read on its last scheduled run;
- the simulated sales system (a JSON response in data/connectors) already has one new opportunity and one bid
  renegotiated at a lower price, so pressing "Sync now" in the demo shows real changes and the bid check reacts.
"""
import json

from sqlalchemy import func, select

from ..models import ErpTransaction, Project, SyncRun
from ..services.connectors import (SALES_SOURCE, STAGE_PROBABILITY, _project_files, fx_usd, now, upsert_opportunities,
                                   waiting_files, write_sales_snapshot)

OWNERS = {"EC": "Andrés Cevallos", "PE": "Lucía Paredes", "BR": "Rafael Monteiro"}

# open and lost bids: value in US dollars (converted to the country's currency at the cut-off rate)
BIDS = [
    dict(crm_id="OPP-2026-014", name="Oleoducto Napo – Tramo C", client="Oriente Crudos S.A.", country="EC", kind="pipeline",
         terrain="rainforest", region="Orellana – Napo", diameter_in=16, length_km=48, stage="submitted", usd=44_200_000, margin=0.15,
         decision="2026-11", modified="2026-09-22",
         step=("Entregar aclaraciones técnicas al cliente", "Send technical clarifications to the client", "Enviar esclarecimentos técnicos ao cliente")),
    dict(crm_id="OPP-2026-019", name="Ducto Selva Central – Tramo 2", client="Selva Energía S.A.C.", country="PE", kind="pipeline",
         terrain="rainforest", region="Junín – Pasco", diameter_in=18, length_km=60, stage="submitted", usd=67_100_000, margin=0.16,
         decision="2026-10", modified="2026-09-15",
         step=("Esperar la evaluación técnica del cliente", "Wait for the client's technical evaluation", "Aguardar a avaliação técnica do cliente")),
    dict(crm_id="OPP-2026-022", name="Gasoducto Costa Sur – Fase 2", client="Costa Hidrocarburos S.A.", country="EC", kind="pipeline",
         terrain="coast", region="Santa Elena – Guayas", diameter_in=10, length_km=38, stage="preparing", usd=13_900_000, margin=0.14,
         decision="2026-12", modified="2026-09-24",
         step=("Visita técnica al trazado programada", "Technical visit to the route scheduled", "Visita técnica ao traçado agendada")),
    dict(crm_id="OPP-2026-025", name="Oleoduto Litoral Norte – Trecho 3", client="Atlântica Dutos S.A.", country="BR", kind="pipeline",
         terrain="coast", region="Bahia – Sergipe", diameter_in=24, length_km=85, stage="submitted", usd=62_700_000, margin=0.13,
         decision="2026-11", modified="2026-09-18",
         step=("Esperar el resultado de la licitación", "Wait for the tender result", "Aguardar o resultado da licitação")),
    dict(crm_id="OPP-2026-027", name="Poliducto Sierra Central", client="Ductos del Pacífico S.A.C.", country="PE", kind="pipeline",
         terrain="highlands", region="Junín – Huancavelica", diameter_in=12, length_km=42, stage="prospecting", usd=30_500_000, margin=0.15,
         decision="2027-02", modified="2026-09-10",
         step=("Reunión inicial con el área de proyectos del cliente", "First meeting with the client's projects team", "Reunião inicial com a área de projetos do cliente")),
    dict(crm_id="OPP-2026-030", name="Estación de Bombeo Coca – Ampliación", client="Oriente Crudos S.A.", country="EC", kind="civil",
         terrain="rainforest", region="Orellana", diameter_in=None, length_km=None, stage="preparing", usd=18_400_000, margin=0.14,
         decision="2026-12", modified="2026-09-19",
         step=("Cotizaciones de equipos de bombeo en curso", "Pump equipment quotes in progress", "Cotações de equipamentos de bombeamento em andamento")),
    dict(crm_id="OPP-2026-031", name="Gasoduto Serra Gaúcha", client="Serra Energia Ltda.", country="BR", kind="pipeline",
         terrain="highlands", region="Rio Grande do Sul", diameter_in=16, length_km=50, stage="preparing", usd=51_700_000, margin=0.14,
         decision="2027-01", modified="2026-09-23",
         step=("Cotizar tubería y revestimiento", "Get pipe and coating prices", "Cotar tubos e revestimento")),
    dict(crm_id="OPP-2026-033", name="Línea de Flujo Tiputini Norte", client="Oriente Crudos S.A.", country="EC", kind="pipeline",
         terrain="rainforest", region="Orellana", diameter_in=8, length_km=20, stage="prospecting", usd=12_100_000, margin=0.17,
         decision="2027-03", modified="2026-09-12",
         step=("Pedir al cliente el estudio de suelos", "Ask the client for the soil study", "Pedir ao cliente o estudo de solos")),
    dict(crm_id="OPP-2025-049", name="Oleoducto Esmeraldas – Variante Norte", client="Costa Hidrocarburos S.A.", country="EC", kind="pipeline",
         terrain="coast", region="Esmeraldas", diameter_in=14, length_km=30, stage="lost", usd=16_200_000, margin=0.15,
         decision="2025-11", modified="2025-11-28", lost_reason="price",
         step=("Nuestro precio quedó 9% por encima del ganador", "Our price was 9% above the winner", "Nosso preço ficou 9% acima do vencedor")),
    dict(crm_id="OPP-2026-004", name="Ducto Talara Sur", client="Ductos del Pacífico S.A.C.", country="PE", kind="pipeline",
         terrain="coast", region="Piura", diameter_in=12, length_km=35, stage="lost", usd=17_800_000, margin=0.14,
         decision="2026-04", modified="2026-04-20", lost_reason="postponed",
         step=("El cliente postergó la inversión a 2027", "The client postponed the investment to 2027", "O cliente adiou o investimento para 2027")),
]

# won bids are the active projects: same value and margin as the project's own records
WON = [("OPP-2024-060", "PE-2410", "2024-09"), ("OPP-2024-081", "BR-2501", "2024-12"), ("OPP-2025-006", "EC-2503", "2025-02"),
       ("OPP-2025-021", "EC-2506", "2025-05"), ("OPP-2025-044", "EC-2511", "2025-10"), ("OPP-2025-058", "PE-2601", "2025-12")]

# what the sales system says now (read on the next sync)
NEW_IN_SOURCE = dict(crm_id="OPP-2026-035", name="Línea de Recolección Loreto – Fase 2", client="Selva Energía S.A.C.", country="PE",
                     kind="pipeline", terrain="rainforest", region="Loreto", diameter_in=8, length_km=18, stage="prospecting",
                     usd=11_400_000, margin=0.16, decision="2027-04", modified="2026-09-27",
                     step=("Oportunidad registrada después de la reunión con el cliente", "Opportunity logged after the client meeting",
                           "Oportunidade registrada após a reunião com o cliente"))
RENEGOTIATED = dict(crm_id="OPP-2026-019", stage="negotiation", usd=63_000_000, modified="2026-09-27",
                    step=("Negociación de precio: el cliente pidió una rebaja de 6%", "Price negotiation: the client asked for a 6% discount",
                          "Negociação de preço: o cliente pediu um desconto de 6%"))


def _record(db, b: dict) -> dict:
    currency = {"EC": "USD", "PE": "PEN", "BR": "BRL"}[b["country"]]
    value = b["usd"] if currency == "USD" else round(b["usd"] / fx_usd(db, currency), -5)
    es, en, pt = b["step"]
    return dict(crm_id=b["crm_id"], name=b["name"], client=b["client"], country=b["country"], kind=b["kind"], terrain=b["terrain"],
                region=b["region"], diameter_in=b["diameter_in"], length_km=b["length_km"], stage=b["stage"], currency=currency,
                value=float(value), bid_margin_pct=b["margin"], probability=STAGE_PROBABILITY[b["stage"]], expected_decision=b["decision"],
                owner=OWNERS[b["country"]], next_step_es=es, next_step_en=en, next_step_pt=pt, project_code=None,
                lost_reason=b.get("lost_reason"), modified_on=b["modified"])


def _won(db) -> list[dict]:
    out = []
    for crm_id, code, decision in WON:
        p = db.scalar(select(Project).where(Project.code == code))
        out.append(dict(crm_id=crm_id, name=p.name, client=p.client, country=p.country_code, kind=p.kind, terrain=p.terrain,
                        region=p.region, diameter_in=p.diameter_in, length_km=p.length_km, stage="won", currency=p.currency,
                        value=p.contract_value, bid_margin_pct=p.bid_margin_pct, probability=1.0, expected_decision=decision,
                        owner=OWNERS[p.country_code], next_step_es="Proyecto en ejecución", next_step_en="Project under way",
                        next_step_pt="Projeto em execução", project_code=code, lost_reason=None, modified_on=f"{decision}-28"))
    return out


def seed_connectors(db) -> None:
    last_read = [_record(db, b) for b in BIDS] + _won(db)
    source = []
    for r in last_read:
        if r["crm_id"] == RENEGOTIATED["crm_id"]:
            es, en, pt = RENEGOTIATED["step"]
            r = dict(_record(db, {**next(b for b in BIDS if b["crm_id"] == r["crm_id"]), "stage": RENEGOTIATED["stage"],
                                  "usd": RENEGOTIATED["usd"], "modified": RENEGOTIATED["modified"]}),
                     next_step_es=es, next_step_en=en, next_step_pt=pt)
        source.append(r)
    source.append(_record(db, NEW_IN_SOURCE))
    SALES_SOURCE.parent.mkdir(parents=True, exist_ok=True)
    SALES_SOURCE.write_text(json.dumps({"@odata.context": "opportunities", "value": source}, ensure_ascii=False, indent=1), encoding="utf-8")

    doc, locs = write_sales_snapshot(db, last_read, now())
    upsert_opportunities(db, last_read, doc, locs)

    # scheduled history (minutes before "now", so the demo never looks stale)
    files = len(_project_files())
    waiting = waiting_files(db)
    folders = len({p.parent for p in _project_files()})
    for m in (4, 19, 34, 49, 64, 79):
        db.add(SyncRun(connector="files", trigger="schedule", offset_minutes=m, duration_ms=1800 + m * 7, status="attention",
                       records_read=files + len(waiting), issues=len(waiting), details=dict(folders=folders, waiting=waiting)))
    gp = db.scalar(select(func.count()).select_from(ErpTransaction)) or 0
    from ..services.reconciliation import reconcile
    rec = reconcile(db)
    for m in (187, 1627, 3067, 4507, 5947):
        db.add(SyncRun(connector="dynamics_gp", trigger="schedule", offset_minutes=m, duration_ms=4200 + m % 900, status="attention",
                       records_read=gp, issues=len(rec["discrepancies"]),
                       details=dict(exports=3, matched=rec["matched"], cells=rec["cells"], differences=len(rec["discrepancies"]))))
    for i, m in enumerate((9, 69, 129, 189, 249, 309)):
        changed = i == 3
        db.add(SyncRun(connector="sales", trigger="schedule", offset_minutes=m, duration_ms=900 + i * 37, status="ok",
                       records_read=len(last_read), records_updated=1 if changed else 0, document_id=doc.id,
                       details=dict(changes=[dict(crm_id="OPP-2026-014", name="Oleoducto Napo – Tramo C", kind="updated",
                                                  fields=[dict(field="stage", old="preparing", new="submitted")])] if changed else [])))
    db.flush()
