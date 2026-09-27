"""Maps free-text activity and cost-type labels (ES/PT/EN, abbreviations) to the
canonical cost breakdown structure. Rules first; Claude handles what rules can't."""
import difflib

from ...i18n import ACTIVITY_NAMES
from .normalize import norm

ACTIVITY_SYNONYMS = {
    "MOV": ["movilizacion", "desmovilizacion", "campamento", "mobilizacao", "canteiro", "mobilization", "camp", "movilizac"],
    "DDV": ["derecho de via", "ddv", "desbroce", "abertura de faixa", "faixa", "right of way", "row", "clearing", "apertura ddv"],
    "ZAN": ["zanja", "zanjeo", "excav", "vala", "trench", "trenching"],
    "TEN": ["tendido", "curvado", "desfile", "curvamento", "stringing", "bending"],
    "SOL": ["soldadura", "soldagem", "welding", "sold"],
    "END": ["radiograf", "end", "ensayos no destructivos", "ensaios nao destrutivos", "ndt", "gammagraf"],
    "REV": ["revestimiento", "revestimento", "coating", "revest"],
    "BAJ": ["bajado", "tapado", "relleno", "abaixamento", "cobertura", "lowering", "backfill"],
    "CRU": ["cruce", "cruces", "phd", "hdd", "travessia", "travessias", "mnd", "crossing", "crossings"],
    "PH": ["prueba hidrostatica", "hidrostat", "teste hidrostatico", "hydrostatic", "hydrotest"],
    "RES": ["restauracion", "revegetacion", "recomposicao", "restoration", "reinstatement"],
    "IND": ["indirectos", "gastos generales", "indiretos", "overhead", "supervision", "gg", "indirect"],
    "EXC": ["movimiento de tierras", "terraplenagem", "earthworks"],
    "CIM": ["cimentacion", "cimentaciones", "hormigon", "concreto", "fundacoes", "obras civis", "foundations", "concrete"],
    "EST": ["estructura metalica", "estructuras metalicas", "estruturas metalicas", "steel structure", "steel structures"],
    "MEC": ["montaje mecanico", "montagem mecanica", "electromecanico", "mechanical installation", "mechanical"],
    "ELE": ["electric", "eletrica", "instrumentacion", "instrumentacao", "instalaciones electricas"],
    "PRU": ["pruebas y", "puesta en marcha", "arranque", "comisionamiento", "comissionamento", "commissioning"],
}

COST_TYPE_SYNONYMS = {
    "MO": ["mano de obra", "mo", "mao de obra", "labor", "labour", "personal", "m o"],
    "EQ": ["equipos", "eq", "equipamentos", "equipment", "maquinaria", "equipo"],
    "MAT": ["materiales", "mat", "materiais", "materials", "material"],
    "SUB": ["subcontratos", "sc", "sub", "subempreiteiros", "subcontracts", "subcontrato", "terceros"],
}


def _matches(tokens: list[str], text: str, syn: str) -> bool:
    if " " in syn:
        return f" {syn} " in f" {text} "
    if len(syn) >= 4:
        return any(t.startswith(syn) for t in tokens)
    return syn in tokens


def map_label(label: str, synonyms: dict[str, list[str]]) -> dict:
    """Returns {code, confidence, method, candidates, note}."""
    text = norm(label)
    tokens = text.split()
    scores = {}
    for code, syns in synonyms.items():
        hit = [s for s in syns if _matches(tokens, text, s)]
        if hit:
            scores[code] = max(len(s) + (6 if " " in s else 0) for s in hit)
    if scores:
        ranked = sorted(scores.items(), key=lambda kv: -kv[1])
        best, best_score = ranked[0]
        if len(ranked) > 1 and ranked[1][1] >= 0.6 * best_score:
            return dict(code=best, confidence=0.6, method="rules", candidates=[c for c, _ in ranked[:3]],
                        note="combined")
        conf = 0.95 if best_score >= 10 else 0.88
        return dict(code=best, confidence=conf, method="rules", candidates=[best], note=None)
    # fuzzy fallback against synonyms and canonical names
    pool = {}
    for code, syns in synonyms.items():
        for s in syns:
            pool[s] = code
        if synonyms is ACTIVITY_SYNONYMS:
            for name in ACTIVITY_NAMES[code]:
                pool[norm(name)] = code
    best = difflib.get_close_matches(text, list(pool), n=1, cutoff=0.55)
    if best:
        ratio = difflib.SequenceMatcher(None, text, best[0]).ratio()
        return dict(code=pool[best[0]], confidence=round(0.45 + ratio * 0.3, 2), method="fuzzy", candidates=[pool[best[0]]], note=None)
    return dict(code=None, confidence=0.0, method="none", candidates=[], note=None)


def map_activity(label: str) -> dict:
    return map_label(label, ACTIVITY_SYNONYMS)


def map_cost_type(label: str) -> dict:
    return map_label(label, COST_TYPE_SYNONYMS)
