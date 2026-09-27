"""Local Ask engine: works with no API key and no internet.

A locally trained intent classifier picks one of 19 question types, a deterministic
extractor finds the project / country / terrain / event category, and a handler
answers with read-only SQL (shown in the trace) or document search (cited). It never
dead-ends: low-confidence questions fall back to document search plus suggestions."""
import re
from collections import defaultdict
from datetime import date

from sqlalchemy.orm import Session

from ...config import STATUS_PERIOD
from ...i18n import COST_TYPES, ISSUE_CATEGORIES, MONTHS, TERRAINS, activity_name, pick
from ...ml import registry
from ...ml.faq import MIN_SCORE as FAQ_MIN
from ...ml.faq import OUT_OF_SCOPE
from ...ml.faq import index as faq_index
from ...ml.intent_model import classify
from ...utils import add_months, last_day
from ..anomalies import portfolio_anomalies
from ..benchmarks import benchmarks
from ..projects import project_detail
from ..quality import report_crosscheck
from ..reconciliation import reconcile
from ..search import INDEX
from .agent import citations
from ..ingestion.normalize import norm
from .sql_guard import run_readonly

MIN_CONFIDENCE = 0.30

SUGGESTIONS = [
    ("margin", "¿Por qué cayó el margen del Oleoducto Amazonía – Tramo B (EC-2503)?", "Why did the margin drop on Oleoducto Amazonía – Tramo B (EC-2503)?", "Por que a margem do Oleoducto Amazonía – Tramo B (EC-2503) caiu?"),
    ("pending", "¿Cuánto tenemos en órdenes de cambio pendientes, por país?", "How much is tied up in pending change orders, by country?", "Quanto temos em ordens de alteração pendentes, por país?"),
    ("status", "¿Cómo va el Ducto Selva Central?", "How is the Selva Central pipeline doing?", "Como está o Duto Selva Central?"),
    ("overruns", "¿Qué proyectos activos tienen sobrecostos y por qué?", "Which active projects are over budget, and why?", "Quais projetos ativos estão acima do orçamento e por quê?"),
    ("quality", "¿Cuadra la contabilidad (Dynamics GP) con el control de costos en Excel?", "Does the accounting system (Dynamics GP) match the Excel cost control?", "A contabilidade (Dynamics GP) bate com o controle de custos em Excel?"),
    ("anomalies", "¿Dónde estamos gastando sin avanzar?", "Where are we spending without making progress?", "Onde estamos gastando sem avançar?"),
    ("days", "¿Qué eventos nos hicieron perder más días en los últimos 12 meses?", "Which events cost us the most lost days in the last 12 months?", "Quais ocorrências nos fizeram perder mais dias nos últimos 12 meses?"),
    ("benchmark", "¿Cuál es nuestro costo histórico por kilómetro en Amazonía frente a la costa?", "What is our historical cost per kilometre in the rainforest compared with the coast?", "Qual é o nosso custo histórico por quilômetro na Amazônia comparado com o litoral?"),
    ("contract", "¿Qué dice el contrato de EC-2503 sobre trabajos adicionales sin orden aprobada?", "What does the EC-2503 contract say about extra work without an approved change order?", "O que diz o contrato do EC-2503 sobre serviços adicionais sem ordem aprovada?"),
]


def suggestions(lang: str) -> list[dict]:
    i = {"es": 1, "en": 2, "pt": 3}.get(lang, 2)
    return [dict(id=s[0], text=s[i]) for s in SUGGESTIONS]


# ---------------------------------------------------------------- formatting

def L(lang, es, en, pt):
    return {"es": es, "en": en, "pt": pt}.get(lang, en)


def _num(x: float, lang: str, d: int = 1) -> str:
    s = f"{x:,.{d}f}"
    return s.replace(",", "\0").replace(".", ",").replace("\0", ".") if lang in ("es", "pt") else s


def usd(x: float, lang: str, cur: str = "USD") -> str:
    sym = {"USD": "USD", "PEN": "S/", "BRL": "R$"}.get(cur, cur)
    a = abs(x)
    s = f"{_num(a / 1e6, lang)} M" if a >= 1e6 else f"{_num(a / 1e3, lang, 0)} k"
    return f"{'−' if x < 0 else ''}{sym} {s}"


def pct(x, lang, d=1):
    return "–" if x is None else f"{_num(x * 100, lang, d)}%"


def pts(x, lang):
    return f"{_num(x * 100, lang)} {L(lang, 'puntos', 'points', 'pontos')}"


def month(p: str, lang: str) -> str:
    m = MONTHS[lang][int(p[5:]) - 1]
    return f"{m.capitalize() if lang == 'en' else m} {p[:4]}"


def ratio(x, lang) -> str:
    return "–" if x is None else _num(x, lang, 2)


def count(n: int, lang: str, es: tuple, en: tuple, pt: tuple) -> str:
    """'1 proyecto activo' / '3 proyectos activos' in the right language."""
    forms = {"es": es, "en": en, "pt": pt}.get(lang, en)
    return f"{n} {forms[0] if n == 1 else forms[1]}"


def H(lang, *cols):
    return [L(lang, *c) if isinstance(c, tuple) else c for c in cols]


class Ctx:
    def __init__(self, db: Session, lang: str, ents: dict, trace: list):
        self.db, self.lang, self.e, self.trace = db, lang, ents, trace

    def sql(self, purpose: str, query: str) -> list[dict]:
        res = run_readonly(query)
        self.trace.append(dict(tool="run_sql", purpose=purpose, query=query.strip(), columns=res["columns"],
                               rows=res["rows"][:50], row_count=len(res["rows"]), truncated=res["truncated"]))
        return [dict(zip(res["columns"], r)) for r in res["rows"]]

    def note(self, what: str):
        self.trace.append(dict(tool="service", purpose=what, query=what))

    def where(self, alias: str = "", with_status: bool = True) -> str:
        a = f"{alias}." if alias else ""
        conds = []
        if self.e.get("countries"):
            conds.append(f"{a}country_code IN ({','.join(repr(c) for c in self.e['countries'])})")
        if self.e.get("terrain"):
            conds.append(f"{a}terrain = '{self.e['terrain']}'")
        if with_status and self.e.get("status"):
            conds.append(f"{a}status = '{self.e['status']}'")
        return "".join(f" AND {c}" for c in conds)


def _ask_project(ctx: Ctx) -> tuple[str, dict]:
    rows = ctx.sql("active projects", "SELECT code, name, health, forecast_margin_pct FROM v_project_overview WHERE status='active' ORDER BY margin_erosion_pts DESC")
    lang = ctx.lang
    text = L(lang, "¿De qué proyecto? Estos son los activos:", "Which project? These are the active ones:", "Qual projeto? Estes são os ativos:")
    return text, dict(columns=H(lang, ("Proyecto", "Project", "Projeto"), ("Nombre", "Name", "Nome"), ("Estado", "Health", "Situação"), ("Margen pronosticado", "Forecast margin", "Margem prevista")),
                      rows=[[r["code"], r["name"], r["health"], pct(r["forecast_margin_pct"], lang)] for r in rows])


# ---------------------------------------------------------------- handlers

def h_portfolio(ctx: Ctx, q: str):
    lang = ctx.lang
    tot = ctx.sql("portfolio totals", """
        SELECT status, COUNT(*) AS n, SUM(contract_value_usd) AS contract_usd, SUM(revised_contract_usd) AS revised_usd,
               SUM(forecast_margin_usd) AS margin_usd, SUM(pending_co_usd) AS pending_usd,
               SUM(CASE WHEN health='red' THEN 1 ELSE 0 END) AS red, SUM(CASE WHEN health='amber' THEN 1 ELSE 0 END) AS amber
        FROM v_project_overview GROUP BY status""")
    act = next((r for r in tot if r["status"] == "active"), None)
    closed = next((r for r in tot if r["status"] == "closed"), {"n": 0})
    rows = ctx.sql("active projects by margin erosion", """
        SELECT code, name, health, bid_margin_pct, forecast_margin_pct, margin_erosion_pts, pending_co_usd
        FROM v_project_overview WHERE status='active' ORDER BY margin_erosion_pts DESC""")
    fm = act["margin_usd"] / act["revised_usd"] if act and act["revised_usd"] else 0
    pending_all = sum(r["pending_usd"] or 0 for r in tot)
    w = rows[0] if rows else None
    text = L(lang,
             f"**{act['n']} proyectos activos** por **{usd(act['contract_usd'], lang)}** de contrato ({closed['n']} cerrados en el histórico). Margen pronosticado del portafolio activo: **{pct(fm, lang)}**. {act['red']} en rojo y {act['amber']} en atención. Órdenes de cambio pendientes: **{usd(pending_all, lang)}**.",
             f"**{act['n']} active projects** worth **{usd(act['contract_usd'], lang)}** in contracts ({closed['n']} closed in the history). Active portfolio forecast margin: **{pct(fm, lang)}**. {act['red']} red and {act['amber']} amber. Pending change orders: **{usd(pending_all, lang)}**.",
             f"**{act['n']} projetos ativos** somando **{usd(act['contract_usd'], lang)}** em contratos ({closed['n']} encerrados no histórico). Margem prevista do portfólio ativo: **{pct(fm, lang)}**. {act['red']} no vermelho e {act['amber']} em atenção. Ordens de alteração pendentes: **{usd(pending_all, lang)}**.")
    if w:
        text += "\n\n" + L(lang,
                           f"El más comprometido es **{w['code']}** ({w['name']}): de {pct(w['bid_margin_pct'], lang)} ofertado a {pct(w['forecast_margin_pct'], lang)} pronosticado.",
                           f"The most exposed is **{w['code']}** ({w['name']}): from {pct(w['bid_margin_pct'], lang)} at bid to {pct(w['forecast_margin_pct'], lang)} forecast.",
                           f"O mais comprometido é o **{w['code']}** ({w['name']}): de {pct(w['bid_margin_pct'], lang)} ofertada para {pct(w['forecast_margin_pct'], lang)} prevista.")
    table = dict(columns=H(lang, ("Proyecto", "Project", "Projeto"), ("Estado", "Health", "Situação"), ("Oferta → pronóstico", "Bid → forecast", "Proposta → previsão"), ("Órdenes de cambio pendientes", "Pending change orders", "Ordens de alteração pendentes")),
                 rows=[[r["code"], r["health"], f"{pct(r['bid_margin_pct'], lang)} → {pct(r['forecast_margin_pct'], lang)}", usd(r["pending_co_usd"], lang)] for r in rows])
    return text, table


def h_overruns(ctx: Ctx, q: str):
    lang = ctx.lang
    rows = ctx.sql("active projects forecasting an overrun", f"""
        SELECT code, name, cpi, cost_overrun_pct, eac_usd, fx_usd, bid_margin_pct, forecast_margin_pct
        FROM v_project_overview WHERE status='active' AND cost_overrun_pct > 0.02{ctx.where(with_status=False)}
        ORDER BY cost_overrun_pct DESC""")
    if not rows:
        return L(lang, "Ningún proyecto activo proyecta sobrecosto con esos filtros.", "No active project forecasts an overrun with those filters.", "Nenhum projeto ativo projeta sobrecusto com esses filtros."), None
    r0 = rows[0]
    lines = [L(lang,
               f"**{count(len(rows), lang, ("proyecto activo", "proyectos activos"), ("active project", "active projects"), ("projeto ativo", "projetos ativos"))}** proyectan sobrecosto al cierre. El más crítico es **{r0['code']}** ({r0['name']}): eficiencia de costo {ratio(r0['cpi'], lang)}, sobrecosto de {pct(r0['cost_overrun_pct'], lang)} y margen pronosticado de {pct(r0['forecast_margin_pct'], lang)} frente a {pct(r0['bid_margin_pct'], lang)} ofertado.",
               f"**{count(len(rows), lang, ("proyecto activo", "proyectos activos"), ("active project", "active projects"), ("projeto ativo", "projetos ativos"))}** forecast a cost overrun at completion. The most critical is **{r0['code']}** ({r0['name']}): cost efficiency {ratio(r0['cpi'], lang)}, {pct(r0['cost_overrun_pct'], lang)} over budget and a forecast margin of {pct(r0['forecast_margin_pct'], lang)} vs. {pct(r0['bid_margin_pct'], lang)} at bid.",
               f"**{count(len(rows), lang, ("proyecto activo", "proyectos activos"), ("active project", "active projects"), ("projeto ativo", "projetos ativos"))}** projetam sobrecusto no encerramento. O mais crítico é o **{r0['code']}** ({r0['name']}): eficiência de custo {ratio(r0['cpi'], lang)}, sobrecusto de {pct(r0['cost_overrun_pct'], lang)} e margem prevista de {pct(r0['forecast_margin_pct'], lang)} contra {pct(r0['bid_margin_pct'], lang)} na proposta."), ""]
    ctx.note("project_detail(): variance drivers by activity")
    trows = []
    for r in rows:
        d = project_detail(ctx.db, r["code"])
        drv = d["drivers"][0] if d["drivers"] else None
        if drv:
            act = activity_name(drv["activity"], lang)
            lines.append(L(lang,
                           f"- **{r['code']}**: la mayor desviación está en {act} ({usd(drv['variance'] * r['fx_usd'], lang)} sobre presupuesto); {len(drv['cos'])} órdenes de cambio sin aprobar y {drv['days_lost']} días perdidos por eventos en esa actividad.",
                           f"- **{r['code']}**: the largest variance is in {act} ({usd(drv['variance'] * r['fx_usd'], lang)} over budget); {len(drv['cos'])} unapproved change orders and {drv['days_lost']} days lost to events on that activity.",
                           f"- **{r['code']}**: o maior desvio está em {act} ({usd(drv['variance'] * r['fx_usd'], lang)} acima do orçamento); {len(drv['cos'])} ordens não aprovadas e {drv['days_lost']} dias perdidos por ocorrências nessa atividade."))
        trows.append([r["code"], ratio(r['cpi'], lang), pct(r["cost_overrun_pct"], lang), usd(r["eac_usd"], lang), activity_name(drv["activity"], lang) if drv else "–"])
    table = dict(columns=H(lang, ("Proyecto", "Project", "Projeto"), ("Eficiencia de costo", "Cost efficiency", "Eficiência de custo"), ("Sobrecosto", "Overrun", "Sobrecusto"), ("Costo estimado al cierre (USD)", "Estimated final cost (USD)", "Custo estimado no término (USD)"), ("Principal causa", "Main driver", "Principal causa")), rows=trows)
    return "\n".join(lines), table


def h_margin(ctx: Ctx, q: str):
    lang, code = ctx.lang, ctx.e.get("project")
    if not code:
        return _ask_project(ctx)
    ctx.note(f"project_detail('{code}'): margin waterfall")
    d = project_detail(ctx.db, code)
    k, p, rate = d["kpis"], d["project"], d["project"]["fx_usd"]
    rev = k["revised_contract"]
    closed = p["status"] == "closed"
    steps = sorted([s for s in d["waterfall"]["steps"] if s["key"] == "activity" and s["value"] < 0], key=lambda s: s["value"])
    head = L(lang,
             f"El margen de **{code}** pasó de {pct(k['bid_margin_pct'], lang)} en la oferta a {pct(k['forecast_margin_pct'], lang)} {'final' if closed else 'pronosticado al cierre'} ({'−' if k['margin_erosion_pts'] > 0 else '+'}{pts(abs(k['margin_erosion_pts']), lang)}).",
             f"**{code}**'s margin went from {pct(k['bid_margin_pct'], lang)} at bid to {pct(k['forecast_margin_pct'], lang)} {'final' if closed else 'forecast at completion'} ({'−' if k['margin_erosion_pts'] > 0 else '+'}{pts(abs(k['margin_erosion_pts']), lang)}).",
             f"A margem do **{code}** passou de {pct(k['bid_margin_pct'], lang)} na proposta para {pct(k['forecast_margin_pct'], lang)} {'final' if closed else 'prevista no encerramento'} ({'−' if k['margin_erosion_pts'] > 0 else '+'}{pts(abs(k['margin_erosion_pts']), lang)}).")
    lines = [head, "", L(lang, "Principales causas:", "Main drivers:", "Principais causas:")] if steps else [head]
    for s in steps[:4]:
        drv = next((x for x in d["drivers"] if x["activity"] == s["code"]), None)
        extra = ""
        if drv and drv["cos"]:
            docs = " ".join(f"[doc:{c['document_id']} p.1]" for c in d["change_orders"] if c["number"] in drv["cos"])
            extra = L(lang, f" — órdenes de cambio sin aprobar relacionadas: {', '.join(drv['cos'])} {docs}", f" — related unapproved change orders: {', '.join(drv['cos'])} {docs}", f" — ordens de alteração não aprovadas relacionadas: {', '.join(drv['cos'])} {docs}")
        elif drv and drv["days_lost"]:
            extra = L(lang, f" — {drv['days_lost']} días perdidos por eventos", f" — {drv['days_lost']} days lost to events", f" — {drv['days_lost']} dias perdidos por ocorrências")
        lines.append(f"- {activity_name(s['code'], lang)}: {usd(s['value'] * rate, lang)} ({pts(-s['value'] / rev, lang)}){extra}")
    pending = [c for c in d["change_orders"] if c["status"] == "pending"]
    if pending:
        tot = sum(c["amount"] for c in pending)
        lines += ["", L(lang,
                        f"Hay **{len(pending)} órdenes de cambio pendientes** por {usd(tot * rate, lang)}; si se aprueban, el margen recuperaría unos {pts(tot / rev, lang)}.",
                        f"There are **{len(pending)} pending change orders** worth {usd(tot * rate, lang)}; if approved, margin would recover about {pts(tot / rev, lang)}.",
                        f"Há **{len(pending)} ordens de alteração pendentes** somando {usd(tot * rate, lang)}; se aprovadas, a margem recuperaria cerca de {pts(tot / rev, lang)}.")]
    return "\n".join(lines), None


def h_pending(ctx: Ctx, q: str):
    lang, code = ctx.lang, ctx.e.get("project")
    extra = f" AND o.code = '{code}'" if code else ctx.where("o", with_status=False)
    rows = ctx.sql("pending change orders", f"""
        SELECT o.code, o.country_code, c.number, c.title_es, c.title_en, c.title_pt, c.amount * o.fx_usd AS amount_usd,
               c.submitted_date, c.cause, d.id AS document_id
        FROM change_orders c JOIN v_project_overview o ON o.project_id = c.project_id
        LEFT JOIN documents d ON d.id = c.document_id
        WHERE c.status = 'pending'{extra} ORDER BY amount_usd DESC""")
    if not rows:
        return L(lang, "No hay órdenes de cambio pendientes con esos filtros.", "There are no pending change orders with those filters.", "Não há ordens de alteração pendentes com esses filtros."), None
    today = date.fromisoformat(last_day(STATUS_PERIOD))
    by_c = defaultdict(lambda: [0, 0.0, 0])
    for r in rows:
        age = (today - date.fromisoformat(r["submitted_date"])).days
        r["age"] = age
        by_c[r["country_code"]][0] += 1
        by_c[r["country_code"]][1] += r["amount_usd"]
        by_c[r["country_code"]][2] = max(by_c[r["country_code"]][2], age)
    total = sum(r["amount_usd"] for r in rows)
    aged = [r for r in rows if r["age"] > 90]
    lines = [L(lang,
               f"Hay **{count(len(rows), lang, ("orden de cambio pendiente", "órdenes de cambio pendientes"), ("pending change order", "pending change orders"), ("ordem de alteração pendente", "ordens de alteração pendentes"))}** por **{usd(total, lang)}**; {len(aged)} con más de 90 días sin resolución.",
               f"There {'is' if len(rows) == 1 else 'are'} **{count(len(rows), lang, ("orden de cambio pendiente", "órdenes de cambio pendientes"), ("pending change order", "pending change orders"), ("ordem de alteração pendente", "ordens de alteração pendentes"))}** totalling **{usd(total, lang)}**; {len(aged)} waiting more than 90 days.",
               f"Há **{count(len(rows), lang, ("orden de cambio pendiente", "órdenes de cambio pendientes"), ("pending change order", "pending change orders"), ("ordem de alteração pendente", "ordens de alteração pendentes"))}** somando **{usd(total, lang)}**; {len(aged)} com mais de 90 dias sem decisão."), ""]
    for r in rows[:5]:
        title = r[f"title_{lang}"]
        lines.append(L(lang, f"- **{r['code']} {r['number']}** ({usd(r['amount_usd'], lang)}, {r['age']} días): {title} [doc:{r['document_id']} p.1]",
                       f"- **{r['code']} {r['number']}** ({usd(r['amount_usd'], lang)}, {r['age']} days): {title} [doc:{r['document_id']} p.1]",
                       f"- **{r['code']} {r['number']}** ({usd(r['amount_usd'], lang)}, {r['age']} dias): {title} [doc:{r['document_id']} p.1]"))
    table = dict(columns=H(lang, ("País", "Country", "País"), ("Órdenes", "Orders", "Ordens"), "USD", ("Más antigua (días)", "Oldest (days)", "Mais antiga (dias)")),
                 rows=[[c, v[0], usd(v[1], lang), v[2]] for c, v in sorted(by_c.items(), key=lambda kv: -kv[1][1])])
    return "\n".join(lines), table


def h_benchmark(ctx: Ctx, q: str):
    lang = ctx.lang
    ctx.note("benchmarks(): closed pipelines, costs escalated to 2026 USD")
    b = benchmarks(ctx.db)["by_terrain"]
    focus = ctx.e.get("terrain") or "rainforest"
    lines = []
    f, co = b.get(focus), b.get("coast")
    if f and co and focus != "coast":
        diff = f["cost_per_km_p50"] / co["cost_per_km_p50"] - 1
        lines.append(L(lang,
                       f"En {TERRAINS[focus]['es']} el costo histórico mediano es **{usd(f['cost_per_km_p50'], lang)} por kilómetro** ({usd(f['cost_per_inch_km_p50'], lang)} por pulgada de diámetro y kilómetro), {pct(diff, lang, 0)} más que en la costa. Esos proyectos cerraron con una mediana de {pts(f['margin_delta_p50'], lang)} frente al margen ofertado y {_num(f['overrun_p50'] * 100, lang)}% de sobrecosto.",
                       f"In the {TERRAINS[focus]['en'].lower()} the median historical cost is **{usd(f['cost_per_km_p50'], lang)} per kilometre** ({usd(f['cost_per_inch_km_p50'], lang)} per inch of diameter per kilometre), {pct(diff, lang, 0)} more than on the coast. Those projects closed a median {pts(f['margin_delta_p50'], lang)} vs. bid margin, with {_num(f['overrun_p50'] * 100, lang)}% overrun.",
                       f"Em {TERRAINS[focus]['pt']} o custo histórico mediano é de **{usd(f['cost_per_km_p50'], lang)} por quilômetro** ({usd(f['cost_per_inch_km_p50'], lang)} por polegada de diâmetro e quilômetro), {pct(diff, lang, 0)} acima do litoral. Esses projetos fecharam com mediana de {pts(f['margin_delta_p50'], lang)} versus a margem ofertada e {_num(f['overrun_p50'] * 100, lang)}% de sobrecusto."))
    elif f:
        lines.append(L(lang, f"En la costa el costo histórico mediano es **{usd(f['cost_per_km_p50'], lang)} por kilómetro**.", f"On the coast the median historical cost is **{usd(f['cost_per_km_p50'], lang)} per kilometre**.", f"No litoral o custo histórico mediano é de **{usd(f['cost_per_km_p50'], lang)} por quilômetro**."))
    lines += ["", L(lang, "Costos en USD de 2026 (escalados 3% anual). Use el estimador en Benchmarks para una oferta concreta.",
                    "Costs in 2026 USD (escalated 3%/year). Use the estimator on the Benchmarks screen for a specific bid.",
                    "Custos em USD de 2026 (reajustados 3% ao ano). Use o estimador na tela Benchmarks para uma proposta específica.")]
    table = dict(columns=H(lang, ("Terreno", "Terrain", "Terreno"), ("Proyectos", "Projects", "Projetos"), ("Dólares por kilómetro (mediana)", "US dollars per kilometre (median)", "Dólares por quilômetro (mediana)"),
                           ("Por pulgada de diámetro y kilómetro", "Per inch of diameter per kilometre", "Por polegada de diâmetro e quilômetro"), ("Margen vs oferta", "Margin vs bid", "Margem vs proposta")),
                 rows=[[TERRAINS[t][lang], v["n"], usd(v["cost_per_km_p50"], lang), usd(v["cost_per_inch_km_p50"], lang), pts(v["margin_delta_p50"], lang)] for t, v in b.items()])
    return "\n".join(lines), table


def h_days(ctx: Ctx, q: str):
    lang, e = ctx.lang, ctx.e
    if e.get("year"):
        period_cond, span = f"i.period LIKE '{e['year']}-%'", e["year"]
    else:
        start = add_months(STATUS_PERIOD, -11)
        period_cond = f"i.period BETWEEN '{start}' AND '{STATUS_PERIOD}'"
        span = L(lang, "los últimos 12 meses", "the last 12 months", "os últimos 12 meses")
    conds = period_cond + (f" AND o.code = '{e['project']}'" if e.get("project") else ctx.where("o", with_status=False))
    if e.get("category"):
        conds += f" AND i.category = '{e['category']}'"
    rows = ctx.sql("events and days lost", f"""
        SELECT o.code, i.period, i.category, i.days_lost, i.cost_impact * o.fx_usd AS impact_usd,
               i.description_es, i.description_en, i.description_pt, i.document_id, i.locator
        FROM issues i JOIN v_project_overview o ON o.project_id = i.project_id
        WHERE {conds} ORDER BY i.days_lost DESC""")
    if not rows:
        return L(lang, f"No hay eventos registrados en {span} con esos filtros.", f"No events recorded in {span} with those filters.", f"Não há ocorrências registradas em {span} com esses filtros."), None
    by_cat = defaultdict(lambda: [0, 0.0, 0])
    for r in rows:
        by_cat[r["category"]][0] += r["days_lost"]
        by_cat[r["category"]][1] += r["impact_usd"]
        by_cat[r["category"]][2] += 1
    ranked = sorted(by_cat.items(), key=lambda kv: -kv[1][0])
    total = sum(v[0] for v in by_cat.values())
    top = ranked[0]
    cat = pick(ISSUE_CATEGORIES[top[0]], lang).lower()
    lines = [L(lang, f"En {span} se perdieron **{total} días** por eventos ({usd(sum(v[1] for v in by_cat.values()), lang)} de impacto). La principal causa: **{cat}** ({top[1][0]} días).",
               f"In {span} we lost **{total} days** to events ({usd(sum(v[1] for v in by_cat.values()), lang)} impact). Main cause: **{cat}** ({top[1][0]} days).",
               f"Em {span} foram perdidos **{total} dias** por ocorrências ({usd(sum(v[1] for v in by_cat.values()), lang)} de impacto). Principal causa: **{cat}** ({top[1][0]} dias)."), ""]
    for r in rows[:4]:
        cite = f" [doc:{r['document_id']} {r['locator']}]" if r["document_id"] else ""
        lines.append(f"- **{r['code']}** ({month(r['period'], lang)}): {r[f'description_{lang}']}{cite}")
    table = dict(columns=H(lang, ("Categoría", "Category", "Categoria"), ("Días perdidos", "Days lost", "Dias perdidos"), ("Impacto (USD)", "Impact (USD)", "Impacto (USD)"), ("Eventos", "Events", "Ocorrências")),
                 rows=[[pick(ISSUE_CATEGORIES[c], lang), v[0], usd(v[1], lang), v[2]] for c, v in ranked])
    return "\n".join(lines), table


CONTRACT_TOPICS = [
    (r"adicional|extra|additional|orden|ordem|change", "trabajo adicional orden de cambio aprobada pago servico adicional ordem aprovada"),
    (r"multa|penal|atraso|delay|late", "multa retraso tope multas atraso"),
    (r"fuerza mayor|force majeure|forca maior|covid|pandem", "fuerza mayor paralizaciones plazo standby forca maior"),
    (r"standby|stand-by", "standby reclamo costos paralizaciones"),
    (r"retenc|retention|retenc|garant", "retencion garantia planilla retencao medicao"),
    (r"pago|payment|pagamento|planilla|medic", "forma de pago planillas avance pagamento medicoes"),
    (r"comunidad|community|comunit", "relacionamiento comunitario paros comunidades"),
    (r"controvers|disput|arbitra", "controversias arbitraje negociacion arbitragem"),
    (r"tuberia|pipe|tubo|suministr|supply", "tuberia suministrada contratante tubos fornecidos"),
]


def h_contract(ctx: Ctx, q: str):
    lang, code = ctx.lang, ctx.e.get("project")
    nq = q.lower()
    terms = " ".join(t for pat, t in CONTRACT_TOPICS if re.search(pat, nq)) or q
    hits = [h for h in INDEX.search(ctx.db, terms, project_code=code, top_k=30) if h["doc_type"] == "contract"][:2]
    ctx.trace.append(dict(tool="search_documents", query=terms, project_code=code,
                          hits=[{k: h[k] for k in ("document_id", "title", "project_code", "page")} for h in hits]))
    if not hits:
        return L(lang, "No encontré esa cláusula en los contratos.", "I could not find that clause in the contracts.", "Não encontrei essa cláusula nos contratos."), None
    who = code or hits[0]["project_code"]
    lines = [L(lang, f"Esto dice el contrato de **{who}**:", f"This is what the **{who}** contract says:", f"Isto é o que diz o contrato do **{who}**:"), ""]
    for h in hits:
        lines.append(f"> {h['snippet']} [doc:{h['document_id']} p.{h['page']}]")
        lines.append("")
    if code:
        pending = ctx.sql("pending change orders on this project", f"SELECT COUNT(*) AS n FROM change_orders c JOIN projects p ON p.id = c.project_id WHERE p.code = '{code}' AND c.status = 'pending'")
        if pending and pending[0]["n"] and re.search(CONTRACT_TOPICS[0][0], nq):
            lines.append(L(lang, f"Relevante porque {code} tiene {pending[0]['n']} órdenes de cambio pendientes, algunas con el trabajo ya ejecutado.",
                           f"This matters because {code} has {pending[0]['n']} pending change orders, some with the work already executed.",
                           f"Isso é relevante porque o {code} tem {pending[0]['n']} ordens pendentes, algumas com o serviço já executado."))
    return "\n".join(lines), None


def h_status(ctx: Ctx, q: str):
    lang, code = ctx.lang, ctx.e.get("project")
    if not code:
        return _ask_project(ctx)
    ctx.note(f"project_detail('{code}')")
    d = project_detail(ctx.db, code)
    p, k = d["project"], d["kpis"]
    rate, cur = p["fx_usd"], "USD"
    health = {"red": L(lang, "crítico", "critical", "crítico"), "amber": L(lang, "en atención", "on watch", "em atenção"), "green": L(lang, "en control", "on track", "sob controle")}[k["health"]]
    if p["status"] == "closed":
        text = L(lang,
                 f"**{code} – {p['name']}** está cerrado ({month(k['as_of_period'], lang)}). Costo final {usd(k['eac'] * rate, lang)}; margen final {pct(k['forecast_margin_pct'], lang)} vs {pct(k['bid_margin_pct'], lang)} ofertado; {k['delay_months']} meses de atraso.",
                 f"**{code} – {p['name']}** is closed ({month(k['as_of_period'], lang)}). Final cost {usd(k['eac'] * rate, lang)}; final margin {pct(k['forecast_margin_pct'], lang)} vs {pct(k['bid_margin_pct'], lang)} at bid; {k['delay_months']} months late.",
                 f"**{code} – {p['name']}** está encerrado ({month(k['as_of_period'], lang)}). Custo final {usd(k['eac'] * rate, lang)}; margem final {pct(k['forecast_margin_pct'], lang)} vs {pct(k['bid_margin_pct'], lang)} ofertada; {k['delay_months']} meses de atraso.")
        return text, None
    lines = [L(lang,
               f"**{code} – {p['name']}** está **{health}**. Avance real {pct(k['progress_pct'], lang, 0)} vs {pct(k['planned_pct'], lang, 0)} programado (eficiencia de plazo {ratio(k['spi'], lang)}); eficiencia de costo {ratio(k['cpi'], lang)}. Costo estimado al cierre {usd(k['eac'] * rate, lang, cur)} y margen pronosticado **{pct(k['forecast_margin_pct'], lang)}** (ofertado {pct(k['bid_margin_pct'], lang)}). Fin pronosticado: {month(p['forecast_finish'], lang)}{'' if not k['delay_months'] else f' (+{k['delay_months']} meses)'}.",
               f"**{code} – {p['name']}** is **{health}**. Actual progress {pct(k['progress_pct'], lang, 0)} vs {pct(k['planned_pct'], lang, 0)} planned (schedule efficiency {ratio(k['spi'], lang)}); cost efficiency {ratio(k['cpi'], lang)}. Estimate at completion {usd(k['eac'] * rate, lang, cur)} and forecast margin **{pct(k['forecast_margin_pct'], lang)}** (bid {pct(k['bid_margin_pct'], lang)}). Forecast finish: {month(p['forecast_finish'], lang)}{'' if not k['delay_months'] else f' (+{k['delay_months']} months)'}.",
               f"**{code} – {p['name']}** está **{health}**. Avanço real {pct(k['progress_pct'], lang, 0)} vs {pct(k['planned_pct'], lang, 0)} previsto (eficiência de prazo {ratio(k['spi'], lang)}); eficiência de custo {ratio(k['cpi'], lang)}. Custo estimado no término {usd(k['eac'] * rate, lang, cur)} e margem prevista **{pct(k['forecast_margin_pct'], lang)}** (ofertada {pct(k['bid_margin_pct'], lang)}). Término previsto: {month(p['forecast_finish'], lang)}{'' if not k['delay_months'] else f' (+{k['delay_months']} meses)'}.")]
    if d["drivers"]:
        drv = d["drivers"][0]
        lines.append("- " + L(lang, f"Mayor desviación: {activity_name(drv['activity'], lang)} ({usd(drv['variance'] * rate, lang)}).",
                              f"Largest variance: {activity_name(drv['activity'], lang)} ({usd(drv['variance'] * rate, lang)}).",
                              f"Maior desvio: {activity_name(drv['activity'], lang)} ({usd(drv['variance'] * rate, lang)})."))
    if k["pending_co_count"]:
        lines.append("- " + L(lang, f"{k['pending_co_count']} órdenes de cambio pendientes por {usd(k['pending_co_value'] * rate, lang)}; la más antigua lleva {k['oldest_pending_days']} días.",
                              f"{k['pending_co_count']} pending change orders worth {usd(k['pending_co_value'] * rate, lang)}; the oldest has waited {k['oldest_pending_days']} days.",
                              f"{k['pending_co_count']} ordens pendentes somando {usd(k['pending_co_value'] * rate, lang)}; a mais antiga espera há {k['oldest_pending_days']} dias."))
    if d["issues"]:
        last = d["issues"][-1]
        cite = f" [doc:{last['document_id']} {last['locator']}]" if last["document_id"] else ""
        lines.append("- " + L(lang, f"Último evento ({month(last['period'], lang)}): {last['descriptions']['es']}{cite}",
                              f"Latest event ({month(last['period'], lang)}): {last['descriptions']['en']}{cite}",
                              f"Última ocorrência ({month(last['period'], lang)}): {last['descriptions']['pt']}{cite}"))
    return "\n".join(lines), None


def h_delays(ctx: Ctx, q: str):
    lang, code = ctx.lang, ctx.e.get("project")
    if code:
        rows = ctx.sql("schedule of the project", f"SELECT code, name, planned_finish_period, forecast_finish_period, delay_months, spi, days_lost_12m FROM v_project_overview WHERE code = '{code}'")
        r = rows[0]
        spi = f" ({L(lang, 'eficiencia de plazo', 'schedule efficiency', 'eficiência de prazo')} {ratio(r['spi'], lang)})" if r["spi"] is not None else ""
        return L(lang,
                 f"**{code}** tenía fin programado en {month(r['planned_finish_period'], lang)} y el pronóstico actual es **{month(r['forecast_finish_period'], lang)}**: {r['delay_months']} meses de atraso{spi}. Días perdidos por eventos en los últimos 12 meses: {r['days_lost_12m']}.",
                 f"**{code}** was planned to finish in {month(r['planned_finish_period'], lang)}; the current forecast is **{month(r['forecast_finish_period'], lang)}**: {r['delay_months']} months late{spi}. Days lost to events in the last 12 months: {r['days_lost_12m']}.",
                 f"**{code}** tinha término previsto em {month(r['planned_finish_period'], lang)} e a previsão atual é **{month(r['forecast_finish_period'], lang)}**: {r['delay_months']} meses de atraso{spi}. Dias perdidos nos últimos 12 meses: {r['days_lost_12m']}."), None
    rows = ctx.sql("delayed active projects", f"""
        SELECT code, name, planned_finish_period, forecast_finish_period, delay_months, spi, days_lost_12m
        FROM v_project_overview WHERE status='active' AND (delay_months > 0 OR spi < 0.95){ctx.where(with_status=False)}
        ORDER BY delay_months DESC, spi""")
    if not rows:
        return L(lang, "Ningún proyecto activo está atrasado.", "No active project is behind schedule.", "Nenhum projeto ativo está atrasado."), None
    r0 = rows[0]
    text = L(lang, f"**{count(len(rows), lang, ("proyecto activo", "proyectos activos"), ("active project", "active projects"), ("projeto ativo", "projetos ativos"))}** con atraso. El mayor atraso es **{r0['code']}**: {count(r0['delay_months'], lang, ("mes", "meses"), ("month", "months"), ("mês", "meses"))} (fin pronosticado {month(r0['forecast_finish_period'], lang)}).",
             f"**{count(len(rows), lang, ("proyecto activo", "proyectos activos"), ("active project", "active projects"), ("projeto ativo", "projetos ativos"))}** behind schedule. The largest delay is **{r0['code']}**: {count(r0['delay_months'], lang, ("mes", "meses"), ("month", "months"), ("mês", "meses"))} (forecast finish {month(r0['forecast_finish_period'], lang)}).",
             f"**{count(len(rows), lang, ("proyecto activo", "proyectos activos"), ("active project", "active projects"), ("projeto ativo", "projetos ativos"))}** com atraso. O maior atraso é o **{r0['code']}**: {count(r0['delay_months'], lang, ("mes", "meses"), ("month", "months"), ("mês", "meses"))} (término previsto {month(r0['forecast_finish_period'], lang)}).")
    table = dict(columns=H(lang, ("Proyecto", "Project", "Projeto"), ("Fin programado", "Planned finish", "Término previsto"), ("Fin pronosticado", "Forecast finish", "Término projetado"), ("Atraso (meses)", "Delay (months)", "Atraso (meses)"), ("Eficiencia de plazo", "Schedule efficiency", "Eficiência de prazo")),
                 rows=[[r["code"], month(r["planned_finish_period"], lang), month(r["forecast_finish_period"], lang), r["delay_months"], ratio(r["spi"], lang)] for r in rows])
    return text, table


def h_countries(ctx: Ctx, q: str):
    lang = ctx.lang
    rows = ctx.sql("active portfolio by country", """
        SELECT country_code, COUNT(*) AS projects, SUM(contract_value_usd) AS contract_usd,
               SUM(forecast_margin_usd) / SUM(revised_contract_usd) AS forecast_margin, SUM(pending_co_usd) AS pending_usd,
               SUM(days_lost_12m) AS days_lost, AVG(cpi) AS avg_cpi
        FROM v_project_overview WHERE status = 'active' GROUP BY country_code ORDER BY forecast_margin DESC""")
    hist = ctx.sql("closed projects by country", """
        SELECT country_code, COUNT(*) AS n, AVG(forecast_margin_pct - bid_margin_pct) AS margin_delta
        FROM v_project_overview WHERE status = 'closed' GROUP BY country_code""")
    hmap = {h["country_code"]: h for h in hist}
    names = {"EC": L(lang, "Ecuador", "Ecuador", "Equador"), "PE": L(lang, "Perú", "Peru", "Peru"), "BR": L(lang, "Brasil", "Brazil", "Brasil")}
    best, worst = rows[0], rows[-1]
    text = L(lang, f"Hoy el mejor margen pronosticado lo tiene **{names[best['country_code']]}** ({pct(best['forecast_margin'], lang)}) y el más bajo **{names[worst['country_code']]}** ({pct(worst['forecast_margin'], lang)}).",
             f"Today **{names[best['country_code']]}** has the best forecast margin ({pct(best['forecast_margin'], lang)}) and **{names[worst['country_code']]}** the lowest ({pct(worst['forecast_margin'], lang)}).",
             f"Hoje a melhor margem prevista é do **{names[best['country_code']]}** ({pct(best['forecast_margin'], lang)}) e a mais baixa do **{names[worst['country_code']]}** ({pct(worst['forecast_margin'], lang)}).")
    table = dict(columns=H(lang, ("País", "Country", "País"), ("Activos", "Active", "Ativos"), ("Contrato (USD)", "Contract (USD)", "Contrato (USD)"), ("Margen pronosticado", "Forecast margin", "Margem prevista"),
                           ("Órdenes de cambio pendientes", "Pending change orders", "Ordens de alteração pendentes"), ("Días perdidos (12 meses)", "Days lost (12 months)", "Dias perdidos (12 meses)"), ("Histórico: margen vs oferta", "History: margin vs bid", "Histórico: margem vs proposta")),
                 rows=[[names[r["country_code"]], r["projects"], usd(r["contract_usd"], lang), pct(r["forecast_margin"], lang), usd(r["pending_usd"], lang), r["days_lost"],
                        pts(hmap[r["country_code"]]["margin_delta"], lang) if r["country_code"] in hmap else "–"] for r in rows])
    return text, table


def h_welds(ctx: Ctx, q: str):
    lang, code = ctx.lang, ctx.e.get("project")
    cond = f" AND o.code = '{code}'" if code else ""
    rows = ctx.sql("latest cumulative weld repair rate per pipeline", f"""
        SELECT o.code, o.name, o.status, pr.period, pr.welds_cum, pr.weld_repairs_cum,
               1.0 * pr.weld_repairs_cum / pr.welds_cum AS repair_rate
        FROM production pr JOIN v_project_overview o ON o.project_id = pr.project_id
        WHERE pr.welds_cum > 0 AND pr.period = (SELECT MAX(p2.period) FROM production p2 WHERE p2.project_id = pr.project_id){cond}
        ORDER BY repair_rate DESC""")
    if not rows:
        return L(lang, "No hay datos de soldadura para ese filtro.", "No welding data for that filter.", "Não há dados de soldagem para esse filtro."), None
    over = [r for r in rows if r["repair_rate"] > 0.05]
    r0 = rows[0]
    text = L(lang, f"La tasa de reparación acumulada más alta es **{r0['code']}** con **{pct(r0['repair_rate'], lang)}** ({r0['weld_repairs_cum']} de {r0['welds_cum']} juntas). {count(len(over), lang, ("proyecto", "proyectos"), ("project", "projects"), ("projeto", "projetos"))} por encima del límite contractual de 5%.",
             f"The highest cumulative weld repair rate is **{r0['code']}** at **{pct(r0['repair_rate'], lang)}** ({r0['weld_repairs_cum']} of {r0['welds_cum']} joints). {count(len(over), lang, ("proyecto", "proyectos"), ("project", "projects"), ("projeto", "projetos"))} above the 5% contract limit.",
             f"A maior taxa de reparo acumulada é do **{r0['code']}** com **{pct(r0['repair_rate'], lang)}** ({r0['weld_repairs_cum']} de {r0['welds_cum']} juntas). {count(len(over), lang, ("proyecto", "proyectos"), ("project", "projects"), ("projeto", "projetos"))} acima do limite contratual de 5%.")
    table = dict(columns=H(lang, ("Proyecto", "Project", "Projeto"), ("Estado", "Status", "Situação"), ("Juntas", "Joints", "Juntas"), ("Reparaciones", "Repairs", "Reparos"), ("Tasa", "Rate", "Taxa")),
                 rows=[[r["code"], r["status"], r["welds_cum"], r["weld_repairs_cum"], pct(r["repair_rate"], lang)] for r in rows])
    return text, table


FLAG_TEXT = {
    "COST_OVERRUN": ("sobrecosto (eficiencia de costo menor a 0,95)", "cost overrun (cost efficiency below 0.95)", "sobrecusto (eficiência de custo abaixo de 0,95)"),
    "SCHEDULE_DELAY": ("atraso", "schedule delay", "atraso"),
    "MARGIN_EROSION": ("margen erosionado", "margin erosion", "erosão de margem"),
    "PENDING_CO": ("órdenes de cambio pendientes por más del 3% del contrato", "pending change orders above 3% of the contract", "ordens de alteração pendentes acima de 3% do contrato"),
    "PENDING_CO_AGING": ("órdenes de cambio con más de 90 días", "change orders older than 90 days", "ordens de alteração com mais de 90 dias"),
    "WELD_QUALITY": ("reparaciones de soldadura > 5%", "weld repairs > 5%", "reparos de solda > 5%"),
}


def h_risks(ctx: Ctx, q: str):
    lang = ctx.lang
    rows = ctx.sql("active projects that need attention", f"""
        SELECT code, name, health, flags, margin_erosion_pts, forecast_margin_pct, pending_co_usd
        FROM v_project_overview WHERE status='active' AND health IN ('red','amber'){ctx.where(with_status=False)}
        ORDER BY CASE health WHEN 'red' THEN 0 ELSE 1 END, margin_erosion_pts DESC""")
    if not rows:
        return L(lang, "Todos los proyectos activos están en control.", "All active projects are on track.", "Todos os projetos ativos estão sob controle."), None
    red = [r for r in rows if r["health"] == "red"]
    lines = [L(lang, f"**{len(red)} proyectos en rojo** y {len(rows) - len(red)} en atención:", f"**{len(red)} red projects** and {len(rows) - len(red)} on watch:", f"**{len(red)} projetos no vermelho** e {len(rows) - len(red)} em atenção:"), ""]
    for r in rows:
        flags = ", ".join(pick(FLAG_TEXT[f], lang) for f in r["flags"].split(",") if f in FLAG_TEXT)
        lines.append(f"- **{r['code']}** ({r['name']}) — {flags}. " + L(lang, f"Margen pronosticado {pct(r['forecast_margin_pct'], lang)}.", f"Forecast margin {pct(r['forecast_margin_pct'], lang)}.", f"Margem prevista {pct(r['forecast_margin_pct'], lang)}."))
    return "\n".join(lines), None


def h_activities(ctx: Ctx, q: str):
    lang, code = ctx.lang, ctx.e.get("project")
    if code:
        ctx.note(f"project_detail('{code}'): cost by activity")
        d = project_detail(ctx.db, code)
        rate = d["project"]["fx_usd"]
        acts = sorted(d["activities"], key=lambda a: -a["variance"])
        over = [a for a in acts if a["variance"] > 0]
        text = L(lang, f"En **{code}**, {len(over)} actividades proyectan sobrecosto; la mayor es **{activity_name(acts[0]['code'], lang)}** ({usd(acts[0]['variance'] * rate, lang)}).",
                 f"On **{code}**, {len(over)} activities forecast an overrun; the largest is **{activity_name(acts[0]['code'], lang)}** ({usd(acts[0]['variance'] * rate, lang)}).",
                 f"No **{code}**, {len(over)} atividades projetam sobrecusto; a maior é **{activity_name(acts[0]['code'], lang)}** ({usd(acts[0]['variance'] * rate, lang)}).")
        rows = [[activity_name(a["code"], lang), usd(a["bac"] * rate, lang), usd(a["ac"] * rate, lang), pct(a["pct"], lang, 0), usd(a["eac"] * rate, lang), usd(a["variance"] * rate, lang)] for a in acts]
    else:
        ctx.note("project_detail() for every active project: variance by activity in USD")
        agg = defaultdict(float)
        codes = [r["code"] for r in ctx.sql("active projects", f"SELECT code FROM v_project_overview WHERE status='active'{ctx.where(with_status=False)}")]
        for c in codes:
            d = project_detail(ctx.db, c)
            for a in d["activities"]:
                agg[a["code"]] += a["variance"] * d["project"]["fx_usd"]
        acts = sorted(agg.items(), key=lambda kv: -kv[1])
        text = L(lang, f"En los proyectos activos, la actividad con más sobrecosto proyectado es **{activity_name(acts[0][0], lang)}** ({usd(acts[0][1], lang)}), seguida de {activity_name(acts[1][0], lang)} ({usd(acts[1][1], lang)}).",
                 f"Across active projects the activity with the largest forecast overrun is **{activity_name(acts[0][0], lang)}** ({usd(acts[0][1], lang)}), followed by {activity_name(acts[1][0], lang)} ({usd(acts[1][1], lang)}).",
                 f"Nos projetos ativos, a atividade com maior sobrecusto previsto é **{activity_name(acts[0][0], lang)}** ({usd(acts[0][1], lang)}), seguida de {activity_name(acts[1][0], lang)} ({usd(acts[1][1], lang)}).")
        rows = [[activity_name(a, lang), "", "", "", "", usd(v, lang)] for a, v in acts[:10]]
    table = dict(columns=H(lang, ("Actividad", "Activity", "Atividade"), ("Presupuesto", "Budget", "Orçamento"), ("Costo real", "Actual", "Custo real"), ("Avance", "Progress", "Avanço"), ("Costo estimado al cierre", "Estimated final cost", "Custo estimado no término"), ("Desviación", "Variance", "Desvio")), rows=rows)
    return text, table


def h_lessons(ctx: Ctx, q: str):
    lang = ctx.lang
    cond = f" AND p.terrain = '{ctx.e['terrain']}'" if ctx.e.get("terrain") else ""
    if ctx.e.get("category") == "geotech" or re.search(r"geot|desliz|landslide|talud", q.lower()):
        cond += " AND p.terrain = 'highlands'"
    rows = ctx.sql("close-out reports", f"""
        SELECT d.id AS document_id, p.code, p.terrain, c.page, c.text
        FROM documents d JOIN projects p ON p.id = d.project_id JOIN document_chunks c ON c.document_id = d.id
        WHERE d.doc_type = 'closeout_report'{cond} ORDER BY p.code, c.page""")
    seen, lessons = set(), []
    for r in rows:
        text = r["text"]
        idx = max(text.find("Lecciones aprendidas"), text.find("Lições aprendidas"))
        if idx < 0:
            continue
        for line in text[idx:].split("\n")[1:]:
            line = line.strip("• ").strip()
            if line and line not in seen:
                seen.add(line)
                lessons.append((line, r["code"], r["document_id"], r["page"]))
    if not lessons:
        return L(lang, "No encontré lecciones aprendidas para ese filtro.", "I found no lessons learned for that filter.", "Não encontrei lições aprendidas para esse filtro."), None
    lines = [L(lang, "Lecciones registradas en los informes de cierre (texto original):", "Lessons recorded in the close-out reports (original text):", "Lições registradas nos relatórios de encerramento (texto original):"), ""]
    for line, code, doc, page in lessons[:6]:
        lines.append(f"- **{code}**: {line} [doc:{doc} p.{page}]")
    return "\n".join(lines), None


def h_list(ctx: Ctx, q: str):
    lang = ctx.lang
    rows = ctx.sql("projects matching the filters", f"""
        SELECT code, name, country_code, status, terrain, kind, contract_value_usd, forecast_margin_pct
        FROM v_project_overview WHERE 1=1{ctx.where()} ORDER BY status, code""")
    if not rows:
        return L(lang, "No hay proyectos con esos filtros.", "No projects match those filters.", "Nenhum projeto corresponde a esses filtros."), None
    act = sum(1 for r in rows if r["status"] == "active")
    text = L(lang, f"**{len(rows)} proyectos** ({act} activos, {len(rows) - act} cerrados) por {usd(sum(r['contract_value_usd'] for r in rows), lang)} de contrato.",
             f"**{len(rows)} projects** ({act} active, {len(rows) - act} closed) worth {usd(sum(r['contract_value_usd'] for r in rows), lang)} in contracts.",
             f"**{len(rows)} projetos** ({act} ativos, {len(rows) - act} encerrados) somando {usd(sum(r['contract_value_usd'] for r in rows), lang)} em contratos.")
    table = dict(columns=H(lang, ("Proyecto", "Project", "Projeto"), ("Nombre", "Name", "Nome"), ("País", "Country", "País"), ("Estado", "Status", "Situação"), ("Terreno", "Terrain", "Terreno"), ("Contrato (USD)", "Contract (USD)", "Contrato (USD)"), ("Margen", "Margin", "Margem")),
                 rows=[[r["code"], r["name"], r["country_code"], r["status"], TERRAINS[r["terrain"]][lang], usd(r["contract_value_usd"], lang), pct(r["forecast_margin_pct"], lang)] for r in rows])
    return text, table


def h_anomalies(ctx: Ctx, q: str):
    lang, code = ctx.lang, ctx.e.get("project")
    ctx.note("anomaly detection: monthly cost vs. cost justified by physical progress, per activity")
    items = [a for a in portfolio_anomalies(ctx.db) if not code or a["project"] == code]
    if not items:
        return L(lang, "No detecté meses con costo sin avance.", "I found no months with cost without progress.", "Não detectei meses com custo sem avanço."), None
    fx = {r["code"]: r["fx_usd"] for r in ctx.sql("FX to USD", "SELECT code, fx_usd FROM v_project_overview")}
    unexplained = [a for a in items if not a["explanation"]]
    lines = [L(lang, f"Detecté **{len(items)} meses con gasto sin avance equivalente**; {len(unexplained)} **no tienen explicación** en ningún informe ni orden de cambio.",
               f"I found **{len(items)} months with spending not matched by progress**; {len(unexplained)} have **no explanation** in any report or change order.",
               f"Detectei **{len(items)} meses com gasto sem avanço equivalente**; {len(unexplained)} **não têm explicação** em nenhum relatório ou ordem de alteração."), ""]
    for a in (unexplained + [x for x in items if x["explanation"]])[:6]:
        exc = usd(a["excess"] * fx.get(a["project"], 1), lang)
        head = f"- **{a['project']}** {month(a['period'], lang)}, {activity_name(a['activity'], lang)}: +{exc}"
        cell = f" [src:{a['document_id']}|{a['locator']}]" if a["document_id"] else ""
        if not a["explanation"]:
            lines.append(head + L(lang, " — **sin explicación, revisar**", " — **unexplained, review**", " — **sem explicação, revisar**") + cell)
        elif a["explanation"]["kind"] == "issue":
            e = a["explanation"]
            lines.append(head + f" — {pick(ISSUE_CATEGORIES[e['category']], lang).lower()} [doc:{e['document_id']} {e['locator']}]" + cell)
        else:
            e = a["explanation"]
            lines.append(head + f" — {e['number']} ({e['status']}) [doc:{e['document_id']} p.1]" + cell)
    return "\n".join(lines), None


def h_quality(ctx: Ctx, q: str):
    lang = ctx.lang
    ctx.note("reconcile(): Dynamics GP ledger vs Excel cost control by project, month and cost type")
    rec = reconcile(ctx.db)
    ctx.note("report_crosscheck(): cumulative cost quoted in each monthly report vs the workbook")
    rc = report_crosscheck(ctx.db)
    kind = {"missing_in_excel": ("registrado en la contabilidad (Dynamics GP) pero no en el Excel", "posted in the accounting system (Dynamics GP) but missing in the Excel", "lançado na contabilidade (Dynamics GP) mas ausente no Excel"),
            "missing_in_erp": ("en el Excel pero aún no en la contabilidad (¿provisión?)", "in the Excel but not yet in the accounting system (accrual?)", "no Excel mas ainda não na contabilidade (provisão?)"),
            "duplicate": ("transacción duplicada en la contabilidad", "transaction duplicated in the accounting system", "transação duplicada na contabilidade")}
    lines = [L(lang,
               f"Concilié **{rec['erp_transactions']} transacciones de Dynamics GP** contra el control de costos: {rec['matched']} de {rec['cells']} combinaciones proyecto-mes-tipo cuadran (**{pct(rec['match_rate'], lang)}** del monto). Diferencias:",
               f"I reconciled **{rec['erp_transactions']} Dynamics GP transactions** against cost control: {rec['matched']} of {rec['cells']} project-month-type cells match (**{pct(rec['match_rate'], lang)}** of the amount). Differences:",
               f"Conciliei **{rec['erp_transactions']} transações do Dynamics GP** com o controle de custos: {rec['matched']} de {rec['cells']} combinações projeto-mês-tipo conferem (**{pct(rec['match_rate'], lang)}** do valor). Diferenças:"), ""]
    for dsc in rec["discrepancies"]:
        erp = dsc["erp_rows"][0] if dsc["erp_rows"] else None
        src = erp if (erp and dsc["kind"] != "missing_in_erp") else (dsc["excel_cells"][0] if dsc["excel_cells"] else None)
        cite = f" [src:{src['document_id']}|{src['locator']}]" if src and src["document_id"] else ""
        lines.append(f"- **{dsc['project']}** {month(dsc['period'], lang)} ({pick(COST_TYPES[dsc['cost_type']], lang).lower()}): {usd(dsc['diff'], lang, dsc['currency'])} — {pick(kind[dsc['kind']], lang)}"
                     + (f" ({erp['reference']})" if erp and dsc["kind"] != "missing_in_erp" else "") + cite)
    lines += ["", L(lang,
                    f"Además, {rc['matched']} de {rc['checked']} informes mensuales coinciden con el Excel en el costo acumulado.",
                    f"Also, {rc['matched']} of {rc['checked']} monthly reports match the Excel on cumulative cost.",
                    f"Além disso, {rc['matched']} de {rc['checked']} relatórios mensais conferem com o Excel no custo acumulado.")]
    for m in rc["mismatches"]:
        lines.append("- " + L(lang,
                              f"**{m['project']}** informe de {month(m['period'], lang)} reporta {usd(m['reported'], lang, m['currency'])} pero el Excel dice {usd(m['workbook'], lang, m['currency'])} [doc:{m['document_id']} p.1]",
                              f"**{m['project']}** {month(m['period'], lang)} report states {usd(m['reported'], lang, m['currency'])} but the Excel says {usd(m['workbook'], lang, m['currency'])} [doc:{m['document_id']} p.1]",
                              f"**{m['project']}** relatório de {month(m['period'], lang)} informa {usd(m['reported'], lang, m['currency'])} mas o Excel diz {usd(m['workbook'], lang, m['currency'])} [doc:{m['document_id']} p.1]"))
    return "\n".join(lines), None


def h_general(ctx: Ctx, q: str, entry: dict | None = None):
    """Concepts, how the system works and small talk, from the built-in knowledge base."""
    lang = ctx.lang
    if entry is None:
        entry, score = faq_index().best(q)
        if score < FAQ_MIN:
            entry = None
    ctx.trace.append(dict(tool="knowledge_base", purpose=entry["id"] if entry else "no match", query=q))
    if not entry:
        return pick(OUT_OF_SCOPE, lang), None
    return pick(entry["a"], lang), None


def h_search(ctx: Ctx, q: str, low_confidence: bool = False):
    lang, code = ctx.lang, ctx.e.get("project")
    hits = INDEX.search(ctx.db, q, project_code=code, top_k=4)
    ctx.trace.append(dict(tool="search_documents", query=q, project_code=code,
                          hits=[{k: h[k] for k in ("document_id", "title", "project_code", "page")} for h in hits]))
    intro = (L(lang, "No estoy seguro de haber entendido la pregunta; esto es lo más relevante que encontré en los documentos:",
               "I'm not sure I understood the question; this is the most relevant content I found in the documents:",
               "Não tenho certeza de ter entendido a pergunta; isto é o mais relevante que encontrei nos documentos:")
             if low_confidence else
             L(lang, "Esto encontré en los documentos:", "This is what I found in the documents:", "Isto é o que encontrei nos documentos:"))
    if not hits:
        return L(lang, "No encontré nada relevante en los documentos. Pruebe con una de las preguntas sugeridas.",
                 "I found nothing relevant in the documents. Try one of the suggested questions.",
                 "Não encontrei nada relevante nos documentos. Tente uma das perguntas sugeridas."), None
    lines = [intro, ""]
    for h in hits[:3]:
        lines.append(f"- **{h['project_code'] or '—'}** · {h['title']}: {h['snippet']} [doc:{h['document_id']} p.{h['page']}]")
    return "\n".join(lines), None


HANDLERS = {
    "portfolio_summary": h_portfolio, "overruns": h_overruns, "margin_project": h_margin, "pending_cos": h_pending,
    "benchmark": h_benchmark, "lost_days": h_days, "contract": h_contract, "project_status": h_status, "delays": h_delays,
    "country_compare": h_countries, "weld_quality": h_welds, "top_risks": h_risks, "activity_costs": h_activities,
    "lessons": h_lessons, "project_list": h_list, "anomalies": h_anomalies, "data_quality": h_quality, "general": h_general,
    "document_search": h_search,
}
DATA_INTENTS = set(HANDLERS) - {"general", "document_search"}
PROJECT_INTENTS = {"margin_project", "project_status", "activity_costs", "contract", "pending_cos", "anomalies"}
SUGGESTION_INTENT = {"margin": "margin_project", "pending": "pending_cos", "status": "project_status", "overruns": "overruns",
                     "quality": "data_quality", "anomalies": "anomalies", "days": "lost_days", "benchmark": "benchmark", "contract": "contract"}

DEFINITION_RE = re.compile(r"^(que es|que son|que significa|que quiere decir|what is|what are|what does|whats|what s|o que e|o que sao|o que significa|define|explain|explica|explique|explicame|meaning of|significado de)\b")
FOLLOWUP_RE = re.compile(r"^(y|e|and|what about|how about|y que tal|ahora|now|agora|tambien|also|e quanto)\b")
ENTITY_KEYS = ("project", "countries", "terrain", "category", "status", "year")

# Suggested next questions after each kind of answer. {code} is the project in focus.
FOLLOWUPS = {
    "margin_project": [("¿Qué órdenes de cambio de {code} están pendientes?", "Which change orders on {code} are pending?", "Quais ordens de alteração do {code} estão pendentes?"),
                       ("¿Dónde está gastando sin avanzar {code}?", "Where is {code} spending without progress?", "Onde o {code} está gastando sem avançar?"),
                       ("¿Qué dice el contrato de {code} sobre trabajos adicionales?", "What does the {code} contract say about extra work?", "O que diz o contrato do {code} sobre serviços adicionais?")],
    "project_status": [("¿Por qué cayó el margen de {code}?", "Why did the margin drop on {code}?", "Por que a margem do {code} caiu?"),
                       ("¿Costos por actividad de {code}?", "Cost by activity for {code}?", "Custos por atividade do {code}?"),
                       ("¿Cuándo termina {code}?", "When will {code} finish?", "Quando termina o {code}?")],
    "pending_cos": [("¿Qué dice el contrato de {code} sobre trabajos adicionales sin orden aprobada?", "What does the {code} contract say about extra work without an approved change order?", "O que diz o contrato do {code} sobre serviços adicionais sem ordem aprovada?"),
                    ("¿Qué es una orden de cambio?", "What is a change order?", "O que é uma ordem de alteração?")],
    "overruns": [("¿Por qué cayó el margen de {code}?", "Why did the margin drop on {code}?", "Por que a margem do {code} caiu?"),
                 ("¿Qué proyectos están atrasados?", "Which projects are behind schedule?", "Quais projetos estão atrasados?")],
    "portfolio_summary": [("¿Qué proyectos están en riesgo?", "Which projects are at risk?", "Quais projetos estão em risco?"),
                          ("¿Cómo se comparan los países?", "How do the countries compare?", "Como os países se comparam?")],
    "delays": [("¿Qué eventos nos hicieron perder más días?", "Which events cost us the most days?", "Quais ocorrências nos fizeram perder mais dias?"),
               ("¿Qué es la eficiencia de plazo?", "What is schedule efficiency?", "O que é eficiência de prazo?")],
    "lost_days": [("¿Dónde estamos gastando sin avanzar?", "Where are we spending without progress?", "Onde estamos gastando sem avançar?"),
                  ("Lecciones aprendidas en la Amazonía", "Lessons learned in the rainforest", "Lições aprendidas na Amazônia")],
    "data_quality": [("¿Dónde estamos gastando sin avanzar?", "Where are we spending without progress?", "Onde estamos gastando sem avançar?"),
                     ("¿Qué es la conciliación?", "What is reconciliation?", "O que é conciliação?")],
    "anomalies": [("¿Cuadra la contabilidad con el Excel?", "Does the accounting system match the Excel?", "A contabilidade bate com o Excel?"),
                  ("¿Qué es el costo sin avance?", "What is cost without progress?", "O que é custo sem avanço?")],
    "benchmark": [("Lecciones aprendidas en la sierra", "Lessons learned in the highlands", "Lições aprendidas na serra"),
                  ("¿Qué es el costo por pulgada-km?", "What is cost per inch-km?", "O que é custo por polegada-km?")],
    "top_risks": [("¿Por qué cayó el margen de {code}?", "Why did the margin drop on {code}?", "Por que a margem do {code} caiu?"),
                  ("¿Cuánto tenemos en órdenes de cambio pendientes?", "How much is in pending change orders?", "Quanto temos em ordens de alteração pendentes?")],
    "country_compare": [("¿Qué proyectos están en riesgo?", "Which projects are at risk?", "Quais projetos estão em risco?")],
    "_default": [("¿Cómo está el portafolio?", "How is the portfolio doing?", "Como está o portfólio?"),
                 ("¿Qué proyectos están en riesgo?", "Which projects are at risk?", "Quais projetos estão em risco?"),
                 ("¿Qué puedes hacer?", "What can you do?", "O que você pode fazer?")],
}


def followups(intent: str, ents: dict, lang: str) -> list[str]:
    code = ents.get("project") or "EC-2503"
    items = FOLLOWUPS.get(intent) or FOLLOWUPS["_default"]
    return [pick(t, lang).format(code=code) for t in items][:3]


def _merge(previous: dict, new: dict) -> dict:
    out = {k: previous.get(k) for k in ENTITY_KEYS}
    for k in ENTITY_KEYS:
        if new.get(k):
            out[k] = new[k]
    if new.get("countries") and not new.get("project"):
        out["project"] = None  # "and in Peru?" moves the focus from a project to a country
    if new.get("project"):
        out["countries"] = []
    out["project_alias"] = new.get("project_alias")
    out["activity"] = new.get("activity")
    return out


def answer(db: Session, question: str, lang: str, context: dict | None = None) -> dict:
    index = registry.project_index(db)
    trace: list[dict] = []
    forced = next((SUGGESTION_INTENT[s[0]] for s in SUGGESTIONS if question.strip() in s[1:]), None)
    cls = classify(registry.intent_model(), index, question)
    intent, conf = (forced, 1.0) if forced else (cls["intent"], cls["confidence"])
    ents = cls["entities"]
    nq = norm(question)
    has_data_entity = bool(ents.get("project") or ents.get("countries") or ents.get("terrain"))
    entry, faq_score = faq_index().best(question)
    route = "data"

    prev = (context or {}).get("intent")
    prev_ents = (context or {}).get("entities") or {}
    if not forced and prev in DATA_INTENTS and (FOLLOWUP_RE.match(nq) or (len(nq.split()) <= 4 and has_data_entity and conf < 0.6)):
        # a follow-up keeps the conversation's focus: "and in Peru?" reuses the question, "and why the margin?" the project
        if not (intent in DATA_INTENTS and conf >= 0.5 and intent != prev):
            intent, conf = prev, max(conf, 0.6)
        route = "followup"
        ents = _merge(prev_ents, ents)
    elif not forced and intent in PROJECT_INTENTS and not ents.get("project") and prev_ents.get("project") and not has_data_entity:
        # "why did the margin drop?" right after talking about a project refers to that project
        ents = _merge(prev_ents, ents)
        route = "followup"
    elif intent == "general":
        # concepts, how the system works, small talk
        if has_data_entity:
            alt = next((a for a, p in cls["alternatives"] if a in DATA_INTENTS), None)
            intent = alt or ("project_status" if ents.get("project") else "portfolio_summary")
        elif faq_score >= FAQ_MIN:
            route = "knowledge"
        else:
            alt = next(((a, p) for a, p in cls["alternatives"] if a in DATA_INTENTS and p >= 0.15), None)
            if alt:
                intent, conf = alt
            else:
                route = "knowledge"
    elif DEFINITION_RE.match(nq) and not has_data_entity and faq_score >= 0.75:
        # "what is X?" without a project or country is a definition, not a data query
        intent, route = "general", "knowledge"
    elif conf < MIN_CONFIDENCE:
        route = "knowledge" if faq_score >= 0.6 else "search"
        intent = "general" if route == "knowledge" else "document_search"

    trace.append(dict(tool="intent", intent=intent, confidence=conf, low_confidence=route == "search", followup=route == "followup",
                      alternatives=cls["alternatives"], entities={k: v for k, v in ents.items() if v and k != "project_alias"}))
    ctx = Ctx(db, lang, ents, trace)
    if route == "knowledge":
        text, table = h_general(ctx, question, entry if faq_score >= FAQ_MIN else None)
    elif route == "search":
        text, table = h_search(ctx, question, low_confidence=True)
    else:
        text, table = HANDLERS[intent](ctx, question)
    res = dict(answer=text, table=table, citations=citations(db, text), trace=trace, engine="local", intent=intent, confidence=conf,
               context=dict(intent=intent, entities={k: ents.get(k) for k in ENTITY_KEYS}),
               followups=followups(intent, ents, lang))
    if route == "search" or (route == "knowledge" and faq_score < FAQ_MIN):
        res["suggestions"] = suggestions(lang)
    return res
