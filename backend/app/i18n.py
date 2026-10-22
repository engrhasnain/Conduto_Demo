"""Reference data and labels in Spanish, English and Portuguese."""

LANGS = ("es", "en", "pt")

# Montamar works across Argentina, out of three operating zones. The
# column is still called "country" in the data model because that is what
# the common model calls it; on screen it reads "Región", and the three
# zones each keep their own cost-sheet format, which is the fragmentation
# the consolidation is for.
COUNTRIES = {
    "NQ": {"es": "Neuquen - Vaca Muerta", "en": "Neuquen - Vaca Muerta", "pt": "Neuquen - Vaca Muerta", "currency": "ARS"},
    "BA": {"es": "Buenos Aires - Litoral", "en": "Buenos Aires - Litoral", "pt": "Buenos Aires - Litoral", "currency": "ARS"},
    "PS": {"es": "Patagonia Sur", "en": "Southern Patagonia", "pt": "Patagonia Sul", "currency": "ARS"},
}

COUNTRY_LANG = {"NQ": "es", "BA": "es", "PS": "es"}

# code, kind, planned window (start, end as fraction of duration), budget weight,
# cost-type split (MO, EQ, MAT, SUB), names
PIPELINE_ACTIVITIES = [
    ("MOV", (0.00, 0.10), 0.06, (0.30, 0.40, 0.15, 0.15)),
    ("DDV", (0.04, 0.45), 0.09, (0.25, 0.60, 0.05, 0.10)),
    ("ZAN", (0.12, 0.58), 0.11, (0.25, 0.60, 0.05, 0.10)),
    ("TEN", (0.16, 0.62), 0.07, (0.35, 0.50, 0.05, 0.10)),
    ("SOL", (0.20, 0.70), 0.17, (0.55, 0.25, 0.15, 0.05)),
    ("END", (0.22, 0.72), 0.04, (0.10, 0.05, 0.05, 0.80)),
    ("REV", (0.24, 0.74), 0.05, (0.35, 0.10, 0.45, 0.10)),
    ("BAJ", (0.28, 0.80), 0.10, (0.30, 0.60, 0.05, 0.05)),
    ("CRU", (0.30, 0.78), 0.09, (0.15, 0.20, 0.10, 0.55)),
    ("PH", (0.74, 0.90), 0.04, (0.35, 0.35, 0.20, 0.10)),
    ("RES", (0.80, 1.00), 0.06, (0.40, 0.40, 0.10, 0.10)),
    ("IND", (0.00, 1.00), 0.12, (0.55, 0.15, 0.20, 0.10)),
]

CIVIL_ACTIVITIES = [
    ("MOV", (0.00, 0.10), 0.06, (0.30, 0.40, 0.15, 0.15)),
    ("EXC", (0.05, 0.30), 0.10, (0.25, 0.60, 0.05, 0.10)),
    ("CIM", (0.15, 0.55), 0.22, (0.35, 0.15, 0.40, 0.10)),
    ("EST", (0.35, 0.70), 0.14, (0.30, 0.15, 0.45, 0.10)),
    ("MEC", (0.45, 0.85), 0.20, (0.40, 0.20, 0.25, 0.15)),
    ("ELE", (0.55, 0.92), 0.12, (0.30, 0.05, 0.35, 0.30)),
    ("PRU", (0.85, 1.00), 0.05, (0.40, 0.20, 0.10, 0.30)),
    ("IND", (0.00, 1.00), 0.11, (0.55, 0.15, 0.20, 0.10)),
]

LINEAR_PROGRESS = {"MOV", "IND"}

# Cathodic protection work, not pipeline construction. The codes are kept
# because the trained label model and every stored cost row are keyed on
# them; what changed is what each one means.
ACTIVITY_NAMES = {
    "MOV": ("Movilizacion y campamentos", "Mobilization & camps", "Mobilizacao e canteiros"),
    "DDV": ("Relevamiento de traza y accesos", "Route survey & access", "Levantamento de traçado e acessos"),
    "ZAN": ("Excavacion para camas anodicas", "Excavation for anode beds", "Escavacao para leitos anodicos"),
    "TEN": ("Tendido de cable de conexion", "Cable laying", "Lançamento de cabo"),
    "SOL": ("Soldaduras exotermicas y conexiones", "Exothermic welds & connections", "Soldas exotermicas e conexoes"),
    "END": ("Mediciones de potencial (CIPS/DCVG)", "Potential surveys (CIPS/DCVG)", "Medicoes de potencial (CIPS/DCVG)"),
    "REV": ("Revestimiento y reparacion de juntas", "Coating & joint repair", "Revestimento e reparo de juntas"),
    "BAJ": ("Instalacion de anodos y relleno", "Anode installation & backfill", "Instalacao de anodos e enchimento"),
    "CRU": ("Dispersores profundos (deep anode beds)", "Deep anode ground beds", "Dispersores profundos"),
    "PH": ("Puesta en servicio y ajuste de rectificadores", "Commissioning & rectifier setting", "Comissionamento e ajuste de retificadores"),
    "RES": ("Restauracion y cierre de obra", "Site restoration & close-out", "Restauracao e encerramento"),
    "IND": ("Indirectos y supervision", "Indirects & supervision", "Indiretos e supervisao"),
    "EXC": ("Movimiento de suelos", "Earthworks", "Movimentacao de solos"),
    "CIM": ("Bases y fundaciones de rectificador", "Rectifier bases & foundations", "Bases e fundacoes de retificador"),
    "EST": ("Montaje de gabinetes y postes", "Cabinets & test post installation", "Montagem de gabinetes e postes"),
    "MEC": ("Montaje de juntas aislantes", "Insulating joint installation", "Montagem de juntas isolantes"),
    "ELE": ("Electricidad, rectificadores e instrumentacion", "Electrical, rectifiers & instrumentation", "Eletrica, retificadores e instrumentacao"),
    "PRU": ("Ensayos y verificacion de criterio", "Testing & criterion verification", "Ensaios e verificacao de criterio"),
}

COST_TYPES = {
    "MO": ("Mano de obra", "Labor", "Mão de obra"),
    "EQ": ("Equipos", "Equipment", "Equipamentos"),
    "MAT": ("Materiales", "Materials", "Materiais"),
    "SUB": ("Subcontratos", "Subcontracts", "Subempreiteiros"),
    "NA": ("Sin desglose", "Not itemized", "Sem detalhamento"),
}
COST_TYPE_ORDER = ["MO", "EQ", "MAT", "SUB"]

TERRAINS = {
    "coast": {"es": "Llanura pampeana", "en": "Pampas plain", "pt": "Planicie pampeana"},
    "highlands": {"es": "Meseta y estepa", "en": "Plateau & steppe", "pt": "Planalto e estepe"},
    "rainforest": {"es": "Monte y zona salina", "en": "Scrub & saline ground", "pt": "Mata e solo salino"},
}

ISSUE_CATEGORIES = {
    "weather": ("Clima / lluvias", "Weather / rain", "Clima / chuvas"),
    "community": ("Conflicto comunitario", "Community stoppage", "Conflito comunitário"),
    "permits": ("Permisos", "Permits", "Licenças"),
    "geotech": ("Geotecnia", "Geotechnical", "Geotecnia"),
    "quality": ("Calidad", "Quality", "Qualidade"),
    "supply": ("Suministros", "Supply", "Suprimentos"),
    "equipment": ("Equipos", "Equipment", "Equipamentos"),
    "force_majeure": ("Fuerza mayor", "Force majeure", "Força maior"),
}

CO_CAUSES = {
    "client_request": ("Solicitud del cliente", "Client request", "Solicitação do cliente"),
    "design": ("Cambio de ingeniería", "Design change", "Mudança de engenharia"),
    "geotech": ("Condición geotécnica", "Geotechnical condition", "Condição geotécnica"),
    "community": ("Standby por conflicto", "Community standby claim", "Standby por conflito"),
    "permits": ("Standby por permisos", "Permit delay claim", "Standby por licenças"),
    "scope": ("Ampliación de alcance", "Scope increase", "Ampliação de escopo"),
    "weather": ("Standby por clima", "Weather standby claim", "Standby por clima"),
    "escalation": ("Reajuste de precios", "Price escalation", "Reajuste de preços"),
}

CO_STATUS = {
    "approved": ("Aprobada", "Approved", "Aprovada"),
    "pending": ("Pendiente", "Pending", "Pendente"),
    "rejected": ("Rechazada", "Rejected", "Rejeitada"),
}

MONTHS = {
    "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
    "en": ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"],
    "pt": ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"],
}


def pick(triple, lang: str) -> str:
    return triple[LANGS.index(lang) if lang in LANGS else 1]


def activity_name(code: str, lang: str) -> str:
    return pick(ACTIVITY_NAMES.get(code, (code, code, code)), lang)


def period_label(period: str, lang: str) -> str:
    y, m = period.split("-")
    return f"{MONTHS.get(lang, MONTHS['en'])[int(m) - 1]}-{y[2:]}"
