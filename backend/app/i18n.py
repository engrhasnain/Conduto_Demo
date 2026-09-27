"""Reference data and labels in Spanish, English and Portuguese."""

LANGS = ("es", "en", "pt")

COUNTRIES = {
    "EC": {"es": "Ecuador", "en": "Ecuador", "pt": "Equador", "currency": "USD"},
    "PE": {"es": "Perú", "en": "Peru", "pt": "Peru", "currency": "PEN"},
    "BR": {"es": "Brasil", "en": "Brazil", "pt": "Brasil", "currency": "BRL"},
}

COUNTRY_LANG = {"EC": "es", "PE": "es", "BR": "pt"}

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

ACTIVITY_NAMES = {
    "MOV": ("Movilización y campamentos", "Mobilization & camps", "Mobilização e canteiros"),
    "DDV": ("Apertura de derecho de vía", "Right-of-way clearing", "Abertura de faixa"),
    "ZAN": ("Excavación de zanja", "Trenching", "Abertura de vala"),
    "TEN": ("Tendido y curvado", "Stringing & bending", "Desfile e curvamento"),
    "SOL": ("Soldadura", "Welding", "Soldagem"),
    "END": ("Ensayos no destructivos", "Non-destructive testing", "Ensaios não destrutivos"),
    "REV": ("Revestimiento de juntas", "Field joint coating", "Revestimento de juntas"),
    "BAJ": ("Bajado y tapado", "Lowering-in & backfill", "Abaixamento e cobertura"),
    "CRU": ("Cruces de ríos y vías (perforación dirigida)", "River and road crossings (directional drilling)", "Travessias de rios e vias (perfuração direcional)"),
    "PH": ("Prueba hidrostática", "Hydrostatic testing", "Teste hidrostático"),
    "RES": ("Restauración ambiental", "Environmental restoration", "Recomposição ambiental"),
    "IND": ("Indirectos y supervisión", "Indirects & supervision", "Indiretos e supervisão"),
    "EXC": ("Movimiento de tierras", "Earthworks", "Terraplenagem"),
    "CIM": ("Cimentaciones y hormigón", "Foundations & concrete", "Fundações e concreto"),
    "EST": ("Estructuras metálicas", "Steel structures", "Estruturas metálicas"),
    "MEC": ("Montaje mecánico", "Mechanical installation", "Montagem mecânica"),
    "ELE": ("Electricidad e instrumentación", "Electrical & instrumentation", "Elétrica e instrumentação"),
    "PRU": ("Pruebas y puesta en marcha", "Testing & commissioning", "Testes e comissionamento"),
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
    "coast": {"es": "Costa", "en": "Coast", "pt": "Litoral"},
    "highlands": {"es": "Sierra / Andes", "en": "Highlands / Andes", "pt": "Serra"},
    "rainforest": {"es": "Amazonía", "en": "Rainforest", "pt": "Floresta amazônica"},
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
