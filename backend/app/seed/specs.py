"""Synthetic project portfolio. Every project and client name is fictional.

Each spec carries a "story" (overrun drivers, events, change orders) that the demo
surfaces through the data. `target_margin` is the final margin for closed projects
and the forecast-at-completion margin for active ones; the simulator calibrates
activity cost performance to land on it.
"""

# Issue: (period, category, activity, days_lost, cost as fraction of budget, params / custom text)
# Change order: dict(number, period, cause, activity, pct of contract, status, executed, params/custom)

ISSUE_TEXT = {
    "weather": (
        "Lluvias intensas y crecida de ríos paralizaron el frente de {act_es} entre el km {km} y el km {km2}. Equipos y cuadrillas en standby durante {days} días.",
        "Heavy rains and river flooding stopped the {act_en} front between km {km} and km {km2}. Equipment and crews on standby for {days} days.",
        "Chuvas intensas e cheia dos rios paralisaram a frente de {act_pt} entre o km {km} e o km {km2}. Equipamentos e equipes em standby por {days} dias.",
    ),
    "community": (
        "Paro comunitario en el km {km} por reclamos de compensación y contratación de mano de obra local. Frente de obra detenido {days} días hasta la firma del acta de acuerdo.",
        "Community stoppage at km {km} over compensation and local-hiring demands. Work front halted for {days} days until an agreement was signed.",
        "Paralisação comunitária no km {km} por reivindicações de compensação e contratação de mão de obra local. Frente de obra parada por {days} dias até a assinatura do acordo.",
    ),
    "permits": (
        "Retraso en la emisión del permiso ambiental para el tramo km {km}–{km2}. Frentes reprogramados; {days} días de afectación.",
        "Delay in the environmental permit for the km {km}–{km2} section. Work fronts rescheduled; {days} days of impact.",
        "Atraso na emissão da licença ambiental para o trecho km {km}–{km2}. Frentes reprogramadas; {days} dias de impacto.",
    ),
    "geotech": (
        "Deslizamiento de talud en el km {km} obligó a estabilizar el derecho de vía y ajustar el trazado. {days} días de afectación.",
        "A slope failure at km {km} required right-of-way stabilization and a route adjustment. {days} days of impact.",
        "Deslizamento de talude no km {km} exigiu estabilização da faixa e ajuste do traçado. {days} dias de impacto.",
    ),
    "quality": (
        "La tasa de reparación de soldaduras alcanzó {rate}% y superó el límite contractual de 5%. Se recalificó a los soldadores y se reforzó la inspección.",
        "Weld repair rate reached {rate}%, above the 5% contractual limit. Welders were requalified and inspection was reinforced.",
        "A taxa de reparo de soldas chegou a {rate}%, acima do limite contratual de 5%. Os soldadores foram requalificados e a inspeção reforçada.",
    ),
    "supply": (
        "Retraso del proveedor en la entrega de materiales; el frente de {act_es} trabajó a capacidad reducida durante {days} días.",
        "Supplier delay in delivering materials; the {act_en} front ran at reduced capacity for {days} days.",
        "Atraso do fornecedor na entrega de materiais; a frente de {act_pt} operou com capacidade reduzida por {days} dias.",
    ),
    "equipment": (
        "Falla de la perforadora direccional en el cruce del km {km}. {days} días hasta la llegada de repuestos.",
        "Directional drilling rig failure at the km {km} crossing. {days} days until spare parts arrived.",
        "Falha da perfuratriz direcional na travessia do km {km}. {days} dias até a chegada das peças.",
    ),
    "force_majeure": (
        "Suspensión de actividades por restricciones sanitarias (COVID-19) dispuestas por la autoridad. {days} días de paralización.",
        "Works suspended due to government health restrictions (COVID-19). {days} days of shutdown.",
        "Suspensão das atividades por restrições sanitárias (COVID-19) determinadas pela autoridade. {days} dias de paralisação.",
    ),
}

CO_TEXT = {
    "client_request": (
        "Cruce adicional de río mediante perforación dirigida en el km {km}, solicitado por el cliente",
        "Additional river crossing by directional drilling at km {km}, requested by the client",
        "Travessia adicional de rio por perfuração direcional no km {km}, solicitada pelo cliente",
    ),
    "design": (
        "Reubicación de la válvula de bloqueo del km {km} por cambio de ingeniería",
        "Relocation of the km {km} block valve due to an engineering change",
        "Realocação da válvula de bloqueio do km {km} por mudança de engenharia",
    ),
    "geotech": (
        "Trabajos adicionales entre el km {km} y el km {km2} por condiciones geotécnicas no previstas",
        "Additional works between km {km} and km {km2} due to unforeseen geotechnical conditions",
        "Serviços adicionais entre o km {km} e o km {km2} por condições geotécnicas não previstas",
    ),
    "community": (
        "Reclamo por standby de equipos y personal durante el paro comunitario",
        "Claim for equipment and crew standby during the community stoppage",
        "Pleito por standby de equipamentos e pessoal durante a paralisação comunitária",
    ),
    "permits": (
        "Reclamo por mayor permanencia en obra por retraso de permisos ambientales",
        "Extended-stay claim due to environmental permit delays",
        "Pleito por permanência estendida devido ao atraso das licenças ambientais",
    ),
    "scope": (
        "Ampliación del campamento para {n} trabajadores adicionales",
        "Camp expansion for {n} additional workers",
        "Ampliação do canteiro para {n} trabalhadores adicionais",
    ),
    "weather": (
        "Reclamo por standby de equipos durante la temporada de lluvias",
        "Claim for equipment standby during the rainy season",
        "Pleito por standby de equipamentos durante a temporada de chuvas",
    ),
    "escalation": (
        "Reajuste del precio de materiales de revestimiento",
        "Price escalation on coating materials",
        "Reajuste do preço dos materiais de revestimento",
    ),
}

GENERIC_LESSONS = {
    "weather": (
        "Programar los frentes de bajado y tapado fuera de la temporada de lluvias e incluir una contingencia de standby climático en la oferta.",
        "Schedule lowering-in and backfill outside the rainy season and price a weather-standby contingency into the bid.",
        "Programar as frentes de abaixamento e cobertura fora da temporada de chuvas e incluir contingência de standby climático na proposta.",
    ),
    "geotech": (
        "Invertir en estudios geotécnicos detallados antes de ofertar tramos de montaña; los sobrecostos de estabilización superaron el 30% de la partida.",
        "Invest in detailed geotechnical studies before bidding mountain sections; stabilization overruns exceeded 30% of the line item.",
        "Investir em estudos geotécnicos detalhados antes de ofertar trechos de serra; os sobrecustos de estabilização superaram 30% do item.",
    ),
    "community": (
        "Firmar acuerdos de relacionamiento comunitario y cupos de empleo local antes de movilizar; cada día de paro costó en promedio 0,06% del presupuesto.",
        "Sign community-relations and local-hiring agreements before mobilizing; each stoppage day cost about 0.06% of budget.",
        "Firmar acordos de relacionamento comunitário e cotas de emprego local antes de mobilizar; cada dia de paralisação custou em média 0,06% do orçamento.",
    ),
    "quality": (
        "Calificar a los soldadores en condiciones reales de obra (altura y humedad) antes de iniciar producción.",
        "Qualify welders under real site conditions (altitude and humidity) before starting production.",
        "Qualificar os soldadores em condições reais de obra (altitude e umidade) antes de iniciar a produção.",
    ),
    "change_orders": (
        "Presentar órdenes de cambio antes de ejecutar el trabajo adicional; el trabajo ejecutado sin aprobación tardó en promedio más de 120 días en cobrarse.",
        "Submit change orders before executing extra work; work executed without approval took over 120 days on average to be recovered.",
        "Apresentar ordens de alteração antes de executar o serviço adicional; o serviço executado sem aprovação levou em média mais de 120 dias para ser recuperado.",
    ),
    "good": (
        "La planificación de frentes paralelos y la alta productividad de soldadura permitieron cerrar con margen superior al ofertado.",
        "Parallel work fronts and high welding productivity allowed the project to close above the bid margin.",
        "A execução em frentes paralelas e a alta produtividade de soldagem permitiram encerrar com margem superior à ofertada.",
    ),
    "covid": (
        "Incluir cláusulas de fuerza mayor con compensación de costos fijos; la paralización por COVID-19 no fue compensada.",
        "Include force-majeure clauses that compensate fixed costs; the COVID-19 shutdown was not compensated.",
        "Incluir cláusulas de força maior com compensação de custos fixos; a paralisação por COVID-19 não foi compensada.",
    ),
}

PROJECTS = [
    # ---------------- ECUADOR (USD) ----------------
    dict(
        code="EC-2503", name="Oleoducto Amazonía – Tramo B", country="EC", client="Oriente Crudos S.A.",
        kind="pipeline", terrain="rainforest", region="Orellana – Sucumbíos", diameter=16, length=62,
        start="2025-03", planned=20, delay=4, status="active", bid=0.17, target=0.045,
        contract_type="lump_sum", manager="Ing. Andrea Villacís",
        stale_report="2026-04",  # the April report repeats March's cumulative cost (caught by the cross-check)
        weights={"CRU": 0.30, "BAJ": 0.25, "SOL": 0.20, "IND": 0.15, "ZAN": 0.10},
        repair=dict(base=0.042, spike=0.081, spike_from=0.20, spike_to=0.36),
        issues=[
            ("2025-05", "weather", "ZAN", 16, 0.009, dict(km=18, km2=26)),
            ("2025-06", "weather", "BAJ", 12, 0.006, dict(km=22, km2=30)),
            ("2025-09", "quality", "SOL", 0, 0.004, dict(rate="8,1")),
            ("2025-10", "community", "IND", 18, 0.011, dict(km=28)),
            ("2026-04", "weather", "BAJ", 14, 0.007, dict(km=38, km2=45)),
            ("2026-05", "weather", "BAJ", 9, 0.005, dict(km=44, km2=50)),
        ],
        cos=[
            dict(number="OC-003", period="2025-07", cause="design", activity="TEN", pct=0.012, status="approved", decision_days=35, executed=1.0, params=dict(km=12)),
            dict(number="OC-005", period="2025-11", cause="scope", activity="MOV", pct=0.008, status="approved", decision_days=41, executed=1.0, params=dict(n=120)),
            dict(number="OC-007", period="2026-02", cause="client_request", activity="CRU", pct=0.029, status="pending", executed=0.95,
                 custom=(
                     "Dos cruces adicionales de río mediante perforación dirigida (río Coca km 34+200 y río Payamino km 41+500), solicitados por el cliente mediante oficio",
                     "Two additional river crossings by directional drilling (Coca river km 34+200 and Payamino river km 41+500), requested by the client in writing",
                     "Duas travessias adicionais de rio por perfuração direcional (rio Coca km 34+200 e rio Payamino km 41+500), solicitadas pelo cliente por ofício",
                 )),
            dict(number="OC-009", period="2026-04", cause="geotech", activity="ZAN", pct=0.014, status="pending", executed=1.0,
                 custom=(
                     "Excavación adicional en roca entre el km 44 y el km 47 por geología no prevista en los estudios del cliente",
                     "Additional rock excavation between km 44 and km 47 due to geology not shown in the client's studies",
                     "Escavação adicional em rocha entre o km 44 e o km 47 por geologia não prevista nos estudos do cliente",
                 )),
            dict(number="OC-010", period="2026-07", cause="community", activity="IND", pct=0.009, status="pending", executed=0.0, params=dict()),
        ],
        description=(
            "Construcción de 62 km de oleoducto de 16\" en la Amazonía ecuatoriana, incluidos cruces especiales de ríos mediante perforación horizontal dirigida.",
            "Construction of 62 km of 16\" crude oil pipeline in the Ecuadorian Amazon, including river crossings by directional drilling.",
            "Construção de 62 km de oleoduto de 16\" na Amazônia equatoriana, incluindo travessias de rios por perfuração direcional.",
        ),
    ),
    dict(
        code="EC-1902", name="Línea de Flujo Sacha Norte", country="EC", client="Oriente Crudos S.A.",
        kind="pipeline", terrain="rainforest", region="Orellana", diameter=10, length=18,
        start="2019-04", planned=11, delay=2, status="closed", bid=0.16, target=0.11,
        contract_type="lump_sum", manager="Ing. Carlos Mora",
        weights={"DDV": 0.30, "BAJ": 0.40, "IND": 0.30},
        repair=dict(base=0.034),
        issues=[
            ("2019-06", "weather", "DDV", 10, 0.006, dict(km=4, km2=9)),
            ("2019-11", "weather", "BAJ", 8, 0.004, dict(km=11, km2=15)),
        ],
        cos=[dict(number="OC-001", period="2019-08", cause="design", activity="TEN", pct=0.02, status="approved", decision_days=28, executed=1.0, params=dict(km=7))],
        lessons=["weather", "change_orders"],
        description=("Línea de flujo de 10\" y 18 km en el campo Sacha.", "18 km, 10\" flowline in the Sacha field.", "Linha de fluxo de 10\" e 18 km no campo Sacha."),
    ),
    dict(
        code="EC-2101", name="Poliducto Costa – Variante Manta", country="EC", client="Costa Hidrocarburos S.A.",
        kind="pipeline", terrain="coast", region="Manabí", diameter=12, length=35,
        start="2021-02", planned=12, delay=0, status="closed", bid=0.15, target=0.18,
        contract_type="unit_price", manager="Ing. Diego Paredes",
        weights={"SOL": 0.30, "ZAN": 0.30, "BAJ": 0.20, "IND": 0.20},
        repair=dict(base=0.026),
        issues=[],
        cos=[dict(number="OC-001", period="2021-06", cause="client_request", activity="CRU", pct=0.03, status="approved", decision_days=21, executed=1.0, params=dict(km=19))],
        lessons=["good"],
        description=("Variante de poliducto de 12\" y 35 km en la costa de Manabí.", "35 km, 12\" products pipeline variant on the Manabí coast.", "Variante de poliduto de 12\" e 35 km no litoral de Manabí."),
    ),
    dict(
        code="EC-2004", name="Oleoducto Andino – Variante Papallacta", country="EC", client="Transandina Energía S.A.",
        kind="pipeline", terrain="highlands", region="Napo – Pichincha", diameter=20, length=28,
        start="2020-01", planned=16, delay=5, status="closed", bid=0.16, target=0.06,
        contract_type="lump_sum", manager="Ing. Lucía Salazar",
        weights={"DDV": 0.35, "CRU": 0.30, "IND": 0.20, "ZAN": 0.15},
        repair=dict(base=0.045),
        issues=[
            ("2020-03", "force_majeure", "IND", 45, 0.012, dict()),
            ("2020-11", "geotech", "DDV", 21, 0.010, dict(km=14)),
            ("2021-02", "weather", "ZAN", 10, 0.004, dict(km=18, km2=22)),
        ],
        cos=[
            dict(number="OC-002", period="2020-12", cause="geotech", activity="DDV", pct=0.03, status="approved", decision_days=64, executed=1.0, params=dict(km=13, km2=16)),
            dict(number="OC-004", period="2021-03", cause="geotech", activity="DDV", pct=0.025, status="rejected", decision_days=95, executed=1.0,
                 custom=(
                     "Reclamo por estabilización adicional de taludes entre el km 16 y el km 19",
                     "Claim for additional slope stabilization between km 16 and km 19",
                     "Pleito por estabilização adicional de taludes entre o km 16 e o km 19",
                 )),
        ],
        lessons=["geotech", "covid", "change_orders"],
        description=("Variante de 28 km de oleoducto de 20\" en zona andina de alta pendiente.", "28 km, 20\" crude pipeline variant through steep Andean terrain.", "Variante de 28 km de oleoduto de 20\" em terreno andino íngreme."),
    ),
    dict(
        code="EC-2506", name="Estación de Bombeo Lago Agrio – Ampliación", country="EC", client="Oriente Crudos S.A.",
        kind="civil", terrain="rainforest", region="Sucumbíos", diameter=None, length=None, civil_budget_usd=14_000_000,
        start="2025-06", planned=16, delay=1, status="active", bid=0.14, target=0.135,
        contract_type="lump_sum", manager="Ing. Pablo Andrade",
        weights={"MEC": 0.5, "CIM": 0.3, "IND": 0.2},
        issues=[
            ("2026-02", "supply", "MEC", 8, 0.002, dict(custom=(
                "Retraso en la entrega de las bombas principales por parte del fabricante; el montaje mecánico se reprogramó 8 días.",
                "The manufacturer delivered the main pumps late; mechanical installation was rescheduled by 8 days.",
                "Atraso do fabricante na entrega das bombas principais; a montagem mecânica foi reprogramada em 8 dias.",
            ))),
        ],
        cos=[dict(number="OC-001", period="2025-10", cause="scope", activity="MEC", pct=0.04, status="approved", decision_days=30, executed=1.0,
                  custom=("Instalación de una bomba adicional y su skid de control", "Installation of an additional pump and control skid", "Instalação de uma bomba adicional e seu skid de controle"))],
        description=("Ampliación de la estación de bombeo: cimentaciones, montaje de dos bombas y sistema eléctrico.", "Pump station expansion: foundations, installation of two pumps and electrical system.", "Ampliação da estação de bombeamento: fundações, montagem de duas bombas e sistema elétrico."),
    ),
    dict(
        code="EC-2511", name="Gasoducto Costa Sur – Fase 1", country="EC", client="Costa Hidrocarburos S.A.",
        kind="pipeline", terrain="coast", region="El Oro – Guayas", diameter=8, length=45,
        start="2025-11", planned=12, delay=0, status="active", bid=0.15, target=0.158,
        contract_type="unit_price", manager="Ing. Diego Paredes",
        weights={"SOL": 0.4, "ZAN": 0.3, "IND": 0.3},
        repair=dict(base=0.024),
        issues=[("2026-03", "weather", "ZAN", 5, 0.002, dict(km=8, km2=12))],
        cos=[],
        description=("Primera fase de 45 km de gasoducto de 8\" en la costa sur.", "Phase 1: 45 km of 8\" gas pipeline on the southern coast.", "Fase 1: 45 km de gasoduto de 8\" no litoral sul."),
    ),
    dict(
        code="EC-2206", name="Línea de Transferencia Shushufindi", country="EC", client="Oriente Crudos S.A.",
        kind="pipeline", terrain="rainforest", region="Sucumbíos", diameter=14, length=24,
        start="2022-06", planned=14, delay=3, status="closed", bid=0.17, target=0.12,
        contract_type="lump_sum", manager="Ing. Andrea Villacís",
        weights={"BAJ": 0.30, "CRU": 0.30, "IND": 0.20, "SOL": 0.20},
        repair=dict(base=0.036),
        issues=[
            ("2023-01", "equipment", "CRU", 9, 0.005, dict(km=11)),
            ("2023-04", "weather", "BAJ", 14, 0.007, dict(km=15, km2=21)),
        ],
        cos=[
            dict(number="OC-001", period="2022-10", cause="client_request", activity="CRU", pct=0.02, status="approved", decision_days=45, executed=1.0, params=dict(km=9)),
            dict(number="OC-003", period="2023-06", cause="weather", activity="IND", pct=0.015, status="pending", executed=0.0, params=dict()),
        ],
        lessons=["weather", "change_orders"],
        description=("Línea de transferencia de 14\" y 24 km entre estaciones de Shushufindi.", "24 km, 14\" transfer line between Shushufindi stations.", "Linha de transferência de 14\" e 24 km entre estações de Shushufindi."),
    ),
    dict(
        code="EC-1908", name="Línea de Flujo Auca Sur", country="EC", client="Oriente Crudos S.A.",
        kind="pipeline", terrain="rainforest", region="Orellana", diameter=6, length=12,
        start="2019-08", planned=8, delay=1, status="closed", bid=0.18, target=0.14,
        contract_type="unit_price", manager="Ing. Carlos Mora",
        weights={"BAJ": 0.5, "IND": 0.5},
        repair=dict(base=0.031),
        issues=[("2019-11", "weather", "BAJ", 7, 0.005, dict(km=5, km2=9))],
        cos=[],
        lessons=["weather"],
        description=("Línea de flujo de 6\" y 12 km en el campo Auca.", "12 km, 6\" flowline in the Auca field.", "Linha de fluxo de 6\" e 12 km no campo Auca."),
    ),
    # ---------------- PERU (PEN) ----------------
    dict(
        code="PE-2410", name="Ducto Selva Central – Tramo 1", country="PE", client="Selva Energía S.A.C.",
        kind="pipeline", terrain="rainforest", region="Junín – Pasco", diameter=18, length=75,
        start="2024-10", planned=24, delay=7, status="active", bid=0.16, target=0.12,
        contract_type="lump_sum", manager="Ing. Rosa Quispe",
        unexplained=[("2025-11", "IND", 0.004)],  # cost spike with no event in any report
        weights={"IND": 0.50, "MOV": 0.20, "DDV": 0.30},
        repair=dict(base=0.033),
        issues=[
            ("2025-02", "permits", "IND", 35, 0.008, dict(km=40, km2=55)),
            ("2025-08", "community", "IND", 22, 0.009, dict(km=31)),
            ("2026-02", "weather", "BAJ", 15, 0.005, dict(km=48, km2=56)),
        ],
        cos=[
            dict(number="OC-002", period="2025-04", cause="design", activity="TEN", pct=0.015, status="approved", decision_days=50, executed=1.0, params=dict(km=22)),
            dict(number="OC-004", period="2026-01", cause="permits", activity="IND", pct=0.018, status="pending", executed=0.0, params=dict()),
        ],
        description=("Primer tramo de 75 km de ducto de 18\" en la selva central.", "First 75 km section of an 18\" pipeline in the central jungle.", "Primeiro trecho de 75 km de duto de 18\" na selva central."),
    ),
    dict(
        code="PE-2202", name="Gasoducto Costa Ica", country="PE", client="Ductos del Pacífico S.A.C.",
        kind="pipeline", terrain="coast", region="Ica", diameter=10, length=40,
        start="2022-02", planned=12, delay=0, status="closed", bid=0.14, target=0.16,
        contract_type="unit_price", manager="Ing. Martín Huamán",
        weights={"SOL": 0.5, "ZAN": 0.5},
        repair=dict(base=0.022),
        issues=[],
        cos=[dict(number="OC-001", period="2022-05", cause="scope", activity="MOV", pct=0.01, status="approved", decision_days=20, executed=1.0, params=dict(n=60))],
        lessons=["good"],
        description=("Gasoducto de 10\" y 40 km en el desierto de Ica.", "40 km, 10\" gas pipeline in the Ica desert.", "Gasoduto de 10\" e 40 km no deserto de Ica."),
    ),
    dict(
        code="PE-2105", name="Poliducto Sierra – Variante Huancayo", country="PE", client="Ductos del Pacífico S.A.C.",
        kind="pipeline", terrain="highlands", region="Junín", diameter=12, length=30,
        start="2021-05", planned=14, delay=3, status="closed", bid=0.15, target=0.09,
        contract_type="lump_sum", manager="Ing. Rosa Quispe",
        weights={"SOL": 0.40, "ZAN": 0.30, "IND": 0.30},
        repair=dict(base=0.055),
        issues=[
            ("2021-10", "quality", "SOL", 0, 0.004, dict(rate="6,8")),
            ("2022-01", "weather", "ZAN", 12, 0.005, dict(km=9, km2=14)),
            ("2022-02", "geotech", "DDV", 10, 0.004, dict(km=21)),
        ],
        cos=[dict(number="OC-002", period="2022-02", cause="geotech", activity="ZAN", pct=0.02, status="approved", decision_days=70, executed=1.0, params=dict(km=20, km2=23))],
        lessons=["quality", "geotech"],
        description=("Variante de poliducto de 12\" y 30 km a más de 3.200 m de altitud.", "30 km, 12\" products pipeline variant above 3,200 m altitude.", "Variante de poliduto de 12\" e 30 km acima de 3.200 m de altitude."),
    ),
    dict(
        code="PE-2303", name="Tanques y Cimentaciones Terminal Callao", country="PE", client="Ductos del Pacífico S.A.C.",
        kind="civil", terrain="coast", region="Callao", diameter=None, length=None, civil_budget_usd=18_000_000,
        start="2023-03", planned=15, delay=1, status="closed", bid=0.14, target=0.13,
        contract_type="lump_sum", manager="Ing. Martín Huamán",
        weights={"CIM": 0.5, "MEC": 0.5},
        issues=[("2023-09", "supply", "EST", 10, 0.003, dict(custom=(
            "Retraso en la entrega de planchas de acero para los tanques; el frente de estructuras trabajó a capacidad reducida 10 días.",
            "Late delivery of steel plates for the tanks; the steel structures front ran at reduced capacity for 10 days.",
            "Atraso na entrega de chapas de aço para os tanques; a frente de estruturas operou com capacidade reduzida por 10 dias.",
        )))],
        cos=[dict(number="OC-001", period="2023-08", cause="scope", activity="MEC", pct=0.03, status="approved", decision_days=33, executed=1.0,
                  custom=("Construcción de un tanque adicional de 20.000 barriles", "Construction of an additional 20,000-barrel tank", "Construção de um tanque adicional de 20.000 barris"))],
        lessons=["change_orders"],
        description=("Cimentaciones y montaje de tanques de almacenamiento en el terminal del Callao.", "Foundations and storage tank erection at the Callao terminal.", "Fundações e montagem de tanques de armazenamento no terminal de Callao."),
    ),
    dict(
        code="PE-2601", name="Línea de Recolección Loreto", country="PE", client="Selva Energía S.A.C.",
        kind="pipeline", terrain="rainforest", region="Loreto", diameter=8, length=22,
        start="2026-01", planned=14, delay=0, status="active", bid=0.17, target=0.165,
        contract_type="unit_price", manager="Ing. Jorge Rivas",
        weights={"DDV": 0.5, "IND": 0.5},
        repair=dict(base=0.03),
        issues=[("2026-03", "weather", "DDV", 7, 0.003, dict(km=3, km2=7))],
        cos=[],
        description=("Línea de recolección de 8\" y 22 km en Loreto.", "22 km, 8\" gathering line in Loreto.", "Linha de coleta de 8\" e 22 km em Loreto."),
    ),
    dict(
        code="PE-2006", name="Ducto Talara Norte", country="PE", client="Ductos del Pacífico S.A.C.",
        kind="pipeline", terrain="coast", region="Piura", diameter=14, length=55,
        start="2020-06", planned=14, delay=3, status="closed", bid=0.15, target=0.12,
        contract_type="lump_sum", manager="Ing. Martín Huamán",
        weights={"IND": 0.5, "MOV": 0.2, "SOL": 0.3},
        repair=dict(base=0.028),
        issues=[("2020-07", "force_majeure", "IND", 30, 0.009, dict())],
        cos=[dict(number="OC-001", period="2020-09", cause="scope", activity="MOV", pct=0.012, status="approved", decision_days=40, executed=1.0,
                  custom=("Implementación de protocolos sanitarios COVID-19 en campamentos", "COVID-19 health protocols in the camps", "Implantação de protocolos sanitários COVID-19 nos canteiros"))],
        lessons=["covid"],
        description=("Ducto de 14\" y 55 km en la costa norte.", "55 km, 14\" pipeline on the northern coast.", "Duto de 14\" e 55 km no litoral norte."),
    ),
    # ---------------- BRAZIL (BRL) ----------------
    dict(
        code="BR-2501", name="Oleoduto Litoral Norte – Trecho 2", country="BR", client="Atlântica Dutos S.A.",
        kind="pipeline", terrain="coast", region="Rio Grande do Norte – Ceará", diameter=24, length=110,
        start="2025-01", planned=26, delay=1, status="active", bid=0.14, target=0.10,
        contract_type="lump_sum", manager="Eng. Fernanda Lima",
        unexplained=[("2026-06", "TEN", 0.004)],
        weights={"REV": 0.40, "END": 0.25, "SOL": 0.20, "IND": 0.15},
        repair=dict(base=0.035, spike=0.062, spike_from=0.50, spike_to=0.58),
        issues=[
            ("2025-09", "supply", "REV", 12, 0.003, dict()),
            ("2026-03", "quality", "SOL", 0, 0.003, dict(rate="6,2")),
        ],
        cos=[
            dict(number="OA-002", period="2025-06", cause="client_request", activity="CRU", pct=0.01, status="approved", decision_days=38, executed=1.0, params=dict(km=64)),
            dict(number="OA-004", period="2026-05", cause="escalation", activity="REV", pct=0.012, status="pending", executed=0.0, params=dict()),
        ],
        description=("Trecho 2 de 110 km de oleoduto de 24\" no litoral nordeste.", "Section 2: 110 km of 24\" crude pipeline on the northeast coast.", "Trecho 2 de 110 km de oleoduto de 24\" no litoral nordeste."),
    ),
    dict(
        code="BR-2203", name="Gasoduto Serra do Mar – Variante", country="BR", client="Serra Energia Ltda.",
        kind="pipeline", terrain="highlands", region="São Paulo", diameter=16, length=38,
        start="2022-03", planned=16, delay=2, status="closed", bid=0.15, target=0.12,
        contract_type="lump_sum", manager="Eng. Ricardo Alves",
        weights={"DDV": 0.4, "CRU": 0.3, "IND": 0.3},
        repair=dict(base=0.038),
        issues=[
            ("2022-11", "geotech", "DDV", 15, 0.007, dict(km=17)),
            ("2023-01", "weather", "BAJ", 12, 0.005, dict(km=22, km2=27)),
        ],
        cos=[dict(number="OA-001", period="2022-12", cause="geotech", activity="DDV", pct=0.025, status="approved", decision_days=55, executed=1.0, params=dict(km=16, km2=19))],
        lessons=["geotech"],
        description=("Variante de 38 km de gasoduto de 16\" na Serra do Mar.", "38 km, 16\" gas pipeline variant in the Serra do Mar.", "Variante de 38 km de gasoduto de 16\" na Serra do Mar."),
    ),
    dict(
        code="BR-2307", name="Base de Bombeamento Manaus", country="BR", client="Atlântica Dutos S.A.",
        kind="civil", terrain="rainforest", region="Amazonas", diameter=None, length=None, civil_budget_usd=11_000_000,
        start="2023-07", planned=14, delay=0, status="closed", bid=0.13, target=0.15,
        contract_type="lump_sum", manager="Eng. Ricardo Alves",
        weights={"CIM": 0.5, "MEC": 0.5},
        issues=[("2024-01", "weather", "EXC", 8, 0.003, dict(km=0, km2=1))],
        cos=[dict(number="OA-001", period="2023-12", cause="scope", activity="ELE", pct=0.02, status="approved", decision_days=25, executed=1.0,
                  custom=("Ampliação do sistema de automação da base", "Expansion of the station automation system", "Ampliação do sistema de automação da base"))],
        lessons=["good"],
        description=("Base de bombeamento com obras civis, montagem mecânica e automação.", "Pump station with civil works, mechanical installation and automation.", "Base de bombeamento com obras civis, montagem mecânica e automação."),
    ),
    dict(
        code="BR-2004", name="Oleoduto Recôncavo", country="BR", client="Atlântica Dutos S.A.",
        kind="pipeline", terrain="coast", region="Bahia", diameter=20, length=64,
        start="2020-04", planned=18, delay=2, status="closed", bid=0.14, target=0.13,
        contract_type="lump_sum", manager="Eng. Fernanda Lima",
        weights={"IND": 0.5, "SOL": 0.5},
        repair=dict(base=0.03),
        issues=[("2020-05", "force_majeure", "IND", 20, 0.006, dict())],
        cos=[dict(number="OA-001", period="2020-10", cause="client_request", activity="CRU", pct=0.015, status="approved", decision_days=42, executed=1.0, params=dict(km=37))],
        lessons=["covid"],
        description=("Oleoduto de 20\" e 64 km no Recôncavo Baiano.", "64 km, 20\" crude pipeline in the Recôncavo region.", "Oleoduto de 20\" e 64 km no Recôncavo Baiano."),
    ),
]
