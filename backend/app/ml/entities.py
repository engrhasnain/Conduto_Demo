"""Entity extraction for questions: project, country, terrain, event category,
status, activity and year. Deterministic, multilingual, accent-insensitive."""
import re

from ..services.ingestion.mapping import map_activity
from ..services.ingestion.normalize import norm

STOP = {"de", "del", "la", "las", "el", "los", "y", "e", "do", "da", "dos", "das", "of", "the", "and", "a", "o", "en", "no", "na", "em"}
COMMON = {
    "oleoducto", "oleoduto", "ducto", "duto", "linea", "flujo", "gasoducto", "gasoduto", "poliducto", "poliduto", "variante",
    "tramo", "trecho", "fase", "estacion", "bombeo", "base", "bombeamento", "ampliacion", "terminal", "tanques", "cimentaciones",
    "recoleccion", "transferencia", "norte", "sur", "central", "costa", "sierra", "selva", "litoral", "amazonia", "serra",
    "ecuador", "equador", "peru", "brasil", "brazil", "proyecto", "projeto", "project", "andino",
}
COUNTRY = {"ecuador": "EC", "equador": "EC", "ecuatoriano": "EC", "peru": "PE", "peruano": "PE", "brasil": "BR", "brazil": "BR", "brasileno": "BR"}
TERRAIN = {
    "rainforest": ["amazonia", "amazonica", "amazonico", "amazonas", "selva", "rainforest", "jungle", "floresta", "oriente"],
    "coast": ["costa", "coast", "coastal", "litoral", "desierto", "desert"],
    "highlands": ["sierra", "andes", "andino", "andina", "highlands", "highland", "serra", "montana", "mountain", "mountains"],
}
CATEGORY = {
    "weather": ["lluvia", "lluvias", "rain", "rains", "chuva", "chuvas", "clima", "weather", "inundacion", "crecida", "flood"],
    "community": ["paro", "paros", "comunidad", "comunidades", "comunitario", "comunitarios", "community", "comunitaria", "paralisacao", "paralisacoes", "protest", "protesta", "stoppage", "stoppages"],
    "permits": ["permiso", "permisos", "permit", "permits", "licencia", "licencias", "licenca", "licencas", "ambiental"],
    "geotech": ["geotecnia", "geotecnico", "deslizamiento", "deslizamientos", "landslide", "landslides", "talud", "deslizamento", "geotech", "roca", "rock"],
    "supply": ["suministro", "suministros", "proveedor", "proveedores", "supply", "supplier", "fornecedor", "materiales"],
    "equipment": ["equipo", "equipos", "falla", "perforadora", "equipment", "breakdown", "maquinaria"],
    "force_majeure": ["covid", "pandemia", "pandemic", "cuarentena", "fuerza", "majeure"],
    "quality": ["calidad", "quality", "qualidade", "reparacion", "reparaciones", "repair"],
}
STATUS = {"active": ["activo", "activos", "active", "ativo", "ativos", "curso", "vigentes"], "closed": ["cerrado", "cerrados", "closed", "encerrado", "encerrados", "historicos", "terminados", "finished"]}

MASKS = {"project": "proyectox", "country": "paisx", "terrain": "terrenox", "category": "eventox"}


class ProjectIndex:
    """Unique unigram and bigram aliases for each project name, plus its code."""

    def __init__(self, projects: list[tuple[str, str]]):
        self.codes = {c for c, _ in projects}
        grams: dict[str, set[str]] = {}
        per_project: dict[str, set[str]] = {}
        for code, name in projects:
            toks = [t for t in norm(name).split() if t not in STOP]
            aliases = {t for t in toks if t not in COMMON and len(t) >= 3}
            aliases |= {f"{a} {b}" for a, b in zip(toks, toks[1:])}
            per_project[code] = aliases
            for a in aliases:
                grams.setdefault(a, set()).add(code)
        self.aliases = {code: {a for a in al if len(grams[a]) == 1} for code, al in per_project.items()}

    def find(self, text: str) -> tuple[str | None, str | None]:
        m = re.search(r"\b([a-z]{2})[\s-]?(\d{4})\b", norm(text))
        if m and f"{m.group(1).upper()}-{m.group(2)}" in self.codes:
            return f"{m.group(1).upper()}-{m.group(2)}", m.group(0)
        toks = [t for t in norm(text).split() if t not in STOP]
        grams = set(toks) | {f"{a} {b}" for a, b in zip(toks, toks[1:])}
        best, best_alias, best_len = None, None, 0
        for code, aliases in self.aliases.items():
            for a in aliases & grams:
                if len(a) > best_len:
                    best, best_alias, best_len = code, a, len(a)
        return best, best_alias


def extract(text: str, index: ProjectIndex) -> dict:
    n = norm(text)
    toks = n.split()
    project, alias = index.find(text)
    alias_toks = set((alias or "").split())
    countries = []
    for t in toks:
        c = COUNTRY.get(t)
        if c and c not in countries and t not in alias_toks:
            countries.append(c)
    terrain = next((k for k, words in TERRAIN.items() for t in toks if t in words and t not in alias_toks), None)
    category = next((k for k, words in CATEGORY.items() for t in toks if t in words), None)
    status = next((k for k, words in STATUS.items() for t in toks if t in words), None)
    year = re.search(r"\b(20\d\d)\b", n)
    act = map_activity(text)
    return dict(
        project=project, project_alias=alias, countries=countries, terrain=terrain, category=category, status=status,
        year=year.group(1) if year else None, activity=act["code"] if act["confidence"] >= 0.85 and act["note"] is None else None,
    )


def mask(text: str, ents: dict) -> str:
    """Replaces entity mentions with placeholders so the intent model learns the question shape, not the names."""
    n = norm(text)
    if ents.get("project_alias"):
        n = n.replace(ents["project_alias"], MASKS["project"])
    toks = []
    for t in n.split():
        if t in COUNTRY:
            toks.append(MASKS["country"])
        elif any(t in w for w in TERRAIN.values()):
            toks.append(MASKS["terrain"])
        elif any(t in w for w in CATEGORY.values()) and t not in ("reparacion", "reparaciones", "repair", "calidad", "quality", "qualidade"):
            toks.append(MASKS["category"])
        else:
            toks.append(t)
    return " ".join(toks)
