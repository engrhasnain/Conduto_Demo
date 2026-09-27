"""Character n-gram classifier that maps cost-line labels (Spanish, Portuguese,
English, abbreviated, misspelled) to the canonical activity codes.

Training data is generated from the activity catalogue, the country templates and
domain phrasing, with augmentations that mimic real spreadsheets (abbreviations,
dropped accents, codes in front, typos). Accuracy is measured on labels written by
hand that the generator never produces."""
import random


from ..i18n import ACTIVITY_NAMES
from ..seed.templates import TEMPLATES
from ..services.ingestion.mapping import ACTIVITY_SYNONYMS
from ..services.ingestion.normalize import norm

OTHER = "OTHER"

EXTRA = {
    "MOV": ["movilizacion de equipos", "desmovilizacion", "campamento temporal", "logistica y campamentos", "mobilizacao de pessoal", "canteiro de obras", "mobilization demobilization", "traslado de maquinaria"],
    "DDV": ["limpieza y desbroce", "nivelacion del derecho de via", "apertura de trocha", "conformacion de ddv", "abertura de pista", "limpeza da faixa", "row clearing and grading", "desmonte y desbroce"],
    "ZAN": ["excavacion de zanja", "zanja en roca", "excavacion en roca", "escavacao de vala", "trenching in rock", "zanjado mecanico"],
    "TEN": ["desfile de tuberia", "tendido de tuberia", "curvado en frio", "doblado de tubos", "desfile de tubos", "pipe stringing", "pipe bending"],
    "SOL": ["soldadura de tuberia", "soldadura principal", "soldagem de tubos", "juntas soldadas", "pipe welding", "soldadura mecanizada", "empalmes soldados"],
    "END": ["radiografia", "gammagrafia", "inspeccion radiografica", "ultrasonido de soldaduras", "ensaios nao destrutivos", "ndt inspection", "inspeccion ut rx"],
    "REV": ["revestimiento de juntas", "mangas termocontraibles", "manta termocontratil", "revestimento de juntas", "field joint coating", "proteccion anticorrosiva"],
    "BAJ": ["bajado de tuberia", "tapado de zanja", "relleno y compactacion", "bajado y relleno", "abaixamento e cobertura", "lowering in", "backfilling"],
    "CRU": ["cruce de rio", "perforacion horizontal dirigida", "cruces especiales", "travessia de rio", "hdd crossing", "cruce de carretera", "cruce subfluvial"],
    "PH": ["prueba hidrostatica", "prueba de presion", "llenado y prueba", "teste hidrostatico", "hydrotest", "pressure test"],
    "RES": ["restauracion del derecho de via", "revegetacion", "reforestacion", "recomposicao ambiental", "reinstatement", "cierre ambiental"],
    "IND": ["gastos generales", "indirectos de obra", "supervision y administracion", "custos indiretos", "overheads", "direccion de obra", "seguros y fianzas"],
    "EXC": ["movimiento de tierras", "excavacion masiva", "terraplenagem", "earthworks", "corte y relleno masivo", "explanacion"],
    "CIM": ["cimentaciones", "hormigon armado", "obras de concreto", "fundacoes", "foundations", "losa de concreto", "zapatas"],
    "EST": ["estructura metalica", "acero estructural", "estruturas metalicas", "steel structures", "montaje de estructuras", "planchas de acero"],
    "MEC": ["montaje mecanico", "montaje de bombas", "montagem mecanica", "mechanical installation", "montaje de tanques", "tuberias de interconexion"],
    "ELE": ["instalaciones electricas", "electricidad e instrumentacion", "eletrica e instrumentacao", "electrical and instrumentation", "tableros electricos", "automatizacion"],
    "PRU": ["pruebas y puesta en marcha", "comisionamiento", "testes e comissionamento", "commissioning", "arranque de planta", "pre comisionamiento"],
}
OTHER_LABELS = [
    "total", "subtotal", "total general", "sub total", "observaciones", "notas", "firma", "elaborado por", "revisado por",
    "aprobado por", "fecha", "pagina", "resumen", "moneda", "tipo de cambio", "iva", "impuestos", "utilidad", "margen",
    "anticipo", "retencion", "saldo", "totais", "observacoes", "assinatura", "comments", "grand total", "notes",
    "signature", "page", "otros ingresos", "descuento", "tipo de costo", "presupuesto", "costo real", "avance",
]

# Written by hand; the generator never produces these exact strings.
TEST_SET = [
    ("Movilizac./campamento", "MOV"), ("Instalación de faenas y campamento", "MOV"), ("Mobilização", "MOV"), ("Mob. y desmob.", "MOV"),
    ("Apertura DDV", "DDV"), ("Desbroce y limpieza", "DDV"), ("Abertura da pista", "DDV"), ("ROW clearing", "DDV"), ("Conformación de trocha", "DDV"),
    ("Excav. zanja", "ZAN"), ("Zanjeo en roca", "ZAN"), ("Escavação de vala", "ZAN"), ("Trench excavation", "ZAN"),
    ("Tendido/curvado", "TEN"), ("Desfile de tubería", "TEN"), ("Curvamento a frio", "TEN"), ("Pipe stringing & bending", "TEN"),
    ("Sold. + END", "SOL"), ("Soldadura línea regular", "SOL"), ("Soldagem", "SOL"), ("Welding - mainline", "SOL"),
    ("Radiografías", "END"), ("Inspección RX/UT", "END"), ("Ensaios radiográficos", "END"), ("NDT", "END"),
    ("Revest. juntas", "REV"), ("Mangas termocontraíbles", "REV"), ("Revestimento", "REV"), ("Joint coating", "REV"),
    ("Bajado/tapado", "BAJ"), ("Relleno de zanja", "BAJ"), ("Abaixamento", "BAJ"), ("Backfill & compaction", "BAJ"),
    ("Cruces rio (PHD)", "CRU"), ("Perforación dirigida río Napo", "CRU"), ("Travessia MND", "CRU"), ("HDD river crossing", "CRU"),
    ("Prueba hidrost.", "PH"), ("Prueba de presión", "PH"), ("Teste de pressão", "PH"), ("Hydrotesting", "PH"),
    ("Restauracion", "RES"), ("Revegetación de DDV", "RES"), ("Recomposição", "RES"), ("Site reinstatement", "RES"),
    ("Indirectos/GG", "IND"), ("Gastos generales de obra", "IND"), ("Custos indiretos", "IND"), ("Site overheads", "IND"),
    ("Mov. de tierras", "EXC"), ("Terraplenagem geral", "EXC"), ("Earthworks & grading", "EXC"),
    ("Hormigón armado", "CIM"), ("Fundações", "CIM"), ("Concrete foundations", "CIM"),
    ("Est. metálicas", "EST"), ("Estrutura metálica", "EST"), ("Structural steel", "EST"),
    ("Montaje de bombas", "MEC"), ("Montagem mecânica", "MEC"), ("Mechanical erection", "MEC"),
    ("Instalaciones eléctricas", "ELE"), ("Elétrica", "ELE"), ("Electrical works", "ELE"),
    ("Puesta en marcha", "PRU"), ("Comissionamento", "PRU"), ("Pre-commissioning", "PRU"),
    ("TOTAL", OTHER), ("Subtotal frente 1", OTHER), ("Observaciones", OTHER), ("Firma del residente", OTHER), ("IVA 12%", OTHER),
    # harder: unusual wording, heavy abbreviation, mixed activities
    ("Campamento + alimentación personal", "MOV"), ("Trocha de acceso", "DDV"), ("Cierre de zanja", "BAJ"), ("Doblez de tubo", "TEN"),
    ("Tie-ins y empalmes", "SOL"), ("Pintura y protección catódica", "REV"), ("Seg. y salud ocupacional", "IND"), ("Llenado, prueba y secado", "PH"),
    ("Encofrado y vaciado", "CIM"), ("Tableros y cableado", "ELE"),
]

SMALL = {"de", "del", "la", "el", "y", "e", "do", "da", "dos", "das", "of", "and", "the", "en", "para"}
PREFIXES = ["", "", "", "01 ", "2 ", "02 00 ", "a ", "item 3 ", "3 1 "]
SUFFIXES = ["", "", "", " phd", " tuberia", " tubos", " km 10 20", " tramo 1", " frente 2"]


def _augment(text: str, rng: random.Random) -> str:
    words = []
    for w in norm(text).split():
        if w in SMALL and rng.random() < 0.4:
            continue
        if len(w) > 5 and rng.random() < 0.3:
            w = w[: rng.randint(3, 5)]
        words.append(w)
    s = " ".join(words) or norm(text)
    if rng.random() < 0.12 and len(s) > 5:
        i = rng.randrange(1, len(s) - 1)
        s = s[:i] + s[i + 1:]
    return (rng.choice(PREFIXES) + s + rng.choice(SUFFIXES)).strip()


def training_data(seed: int = 7, per_base: int = 10) -> tuple[list[str], list[str]]:
    rng = random.Random(seed)
    X, y = [], []
    for code, names in ACTIVITY_NAMES.items():
        bases = set(names) | {t["labels"][code] for t in TEMPLATES.values()} | set(EXTRA.get(code, []))
        bases |= {s for s in ACTIVITY_SYNONYMS.get(code, []) if len(s) >= 4}
        for b in bases:
            X.append(b)
            y.append(code)
            for _ in range(per_base):
                X.append(_augment(b, rng))
                y.append(code)
    for b in OTHER_LABELS:
        for _ in range(4):
            X.append(_augment(b, rng))
            y.append(OTHER)
    return X, y


def train():
    # scikit-learn is only needed to train (at build time); prediction unpickles the saved model
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    X, y = training_data()
    model = make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, preprocessor=norm),
        LogisticRegression(C=10, max_iter=4000, class_weight="balanced"),
    )
    model.fit(X, y)
    labels = [t for t, _ in TEST_SET]
    truth = [c for _, c in TEST_SET]
    proba = model.predict_proba(labels)
    classes = list(model.classes_)
    top1 = [str(classes[row.argmax()]) for row in proba]
    top2 = [[str(classes[i]) for i in row.argsort()[::-1][:2]] for row in proba]
    metrics = dict(
        name="label_mapper", algorithm="TF-IDF (char 2-5 grams) + logistic regression",
        n_train=len(X), n_test=len(TEST_SET), classes=len(classes),
        accuracy=sum(p == t for p, t in zip(top1, truth)) / len(truth),
        top2_accuracy=sum(t in p for p, t in zip(top2, truth)) / len(truth),
        errors=[dict(label=l, expected=t, predicted=p) for l, t, p in zip(labels, truth, top1) if p != t],
    )
    return model, metrics


def predict(model, labels: list[str]) -> list[dict]:
    if not labels:
        return []
    classes = [str(c) for c in model.classes_]
    out = []
    for row in model.predict_proba(labels):
        order = row.argsort()[::-1]
        best = classes[order[0]]
        out.append(dict(
            code=None if best == OTHER else best, confidence=round(float(row[order[0]]), 3),
            top=[(classes[i], round(float(row[i]), 3)) for i in order[:3]],
        ))
    return out
