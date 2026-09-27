"""Question-intent classifier for the local (no-API) Ask engine.

Trained on paraphrase templates in Spanish, English and Portuguese with entities
masked, so it learns the shape of a question rather than project names. Accuracy
is measured on questions written by hand that are not in the templates."""
import random

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline, make_union

from ..seed.specs import PROJECTS
from .entities import ProjectIndex, extract, mask

P = [p["code"] for p in PROJECTS] + [p["name"] for p in PROJECTS] + [
    "tramo B", "Selva Central", "Litoral Norte", "Papallacta", "Manta", "Sacha Norte", "Shushufindi", "Huancayo", "Talara", "Serra do Mar", "Lago Agrio", "Costa Sur"]
C = ["Ecuador", "Perú", "Brasil", "Brazil", "Peru", "Equador"]
T = ["la Amazonía", "la selva", "la costa", "la sierra", "los Andes", "the rainforest", "the coast", "the highlands", "Amazônia", "litoral", "serra"]
K = ["lluvias", "paros comunitarios", "permisos", "deslizamientos", "clima", "rain", "community stoppages", "permits", "landslides", "chuvas", "paralisações", "licenças"]
A = ["soldadura", "cruces especiales", "zanjeo", "indirectos", "welding", "HDD crossings", "trenching", "soldagem", "travessias"]
G = ["el margen", "una orden de cambio", "el valor ganado", "la eficiencia de costo", "el CPI", "la curva S", "el derecho de vía", "la prueba hidrostática",
     "el standby", "la conciliación", "la trazabilidad", "a change order", "earned value", "cost efficiency", "an S-curve", "the right of way",
     "a hydrotest", "reconciliation", "a margem", "uma ordem de alteração", "o valor agregado", "a eficiência de prazo", "force majeure", "an ERP"]

TEMPLATES = {
    "portfolio_summary": [
        "¿Cómo está el portafolio?", "Dame un resumen del portafolio", "resumen general de los proyectos", "¿cómo vamos en general?",
        "estado general de la cartera", "¿cuál es el margen total del portafolio?", "¿cuánto contrato tenemos activo?", "resumen ejecutivo",
        "How is the portfolio doing?", "Give me a portfolio overview", "overall status of our projects", "what's our total forecast margin",
        "executive summary", "how much active contract value do we have", "Como está o portfólio?", "Resumo geral dos projetos",
        "qual a margem total prevista", "resumo executivo",
    ],
    "overruns": [
        "¿Qué proyectos tienen sobrecostos?", "¿Qué proyectos están por encima del presupuesto?", "¿dónde estamos gastando de más?",
        "proyectos con sobrecosto en {c}", "¿qué obras se pasaron del presupuesto?", "proyectos con CPI bajo", "¿hay proyectos con desviación de costos?",
        "Which projects are over budget?", "Where are we overspending?", "cost overruns in {c}", "projects with low CPI", "which jobs exceed their budget",
        "Quais projetos estão acima do orçamento?", "onde estamos gastando demais", "obras com sobrecusto no {c}", "projetos com CPI baixo",
    ],
    "margin_project": [
        "¿Por qué cayó el margen de {p}?", "¿Qué pasó con el margen de {p}?", "¿cuál es el margen de {p}?", "margen pronosticado de {p}",
        "¿dónde se pierde el margen en {p}?", "¿por qué {p} está perdiendo dinero?", "Why did the margin drop on {p}?", "What happened to {p}'s margin?",
        "forecast margin for {p}", "where is {p} losing money", "why is {p} losing margin", "Por que a margem do {p} caiu?", "qual é a margem do {p}",
        "onde o {p} está perdendo dinheiro",
    ],
    "pending_cos": [
        "¿Cuánto tenemos en órdenes de cambio pendientes?", "órdenes de cambio sin aprobar", "OC pendientes en {c}", "¿qué órdenes de cambio de {p} siguen pendientes?",
        "reclamos pendientes con el cliente", "¿cuánto nos deben por trabajos adicionales?", "órdenes de cambio con más de 90 días",
        "How much is in pending change orders?", "unapproved change orders in {c}", "pending COs for {p}", "outstanding claims with clients",
        "change orders older than 90 days", "Quanto temos em ordens de alteração pendentes?", "ordens de alteração não aprovadas",
        "pleitos pendentes com o cliente", "OAs pendentes do {p}",
    ],
    "benchmark": [
        "¿Cuánto cuesta un km de ducto en {t}?", "costo histórico por kilómetro", "¿cuál es nuestro costo por km en {t}?", "benchmark de costos por terreno",
        "costo por pulgada-km", "¿cuánto deberíamos ofertar por km en {t}?", "How much does a km of pipeline cost in {t}?", "historical cost per km",
        "cost per inch-km by terrain", "benchmark our costs", "what should we bid per km in {t}", "Quanto custa um km de duto na {t}?",
        "custo histórico por quilômetro", "custo por polegada-km",
    ],
    "lost_days": [
        "¿Qué eventos nos hicieron perder más días?", "¿cuántos días perdimos por {k}?", "días perdidos en {c}", "impacto de las {k} en los proyectos",
        "¿cuántos paros hubo este año?", "eventos que afectaron a {p}", "Which events cost us the most days?", "how many days did we lose to {k}",
        "days lost in {c}", "impact of {k} on our projects", "events affecting {p}", "Quais ocorrências nos fizeram perder mais dias?",
        "quantos dias perdemos por {k}", "impacto das {k} nos projetos",
    ],
    "contract": [
        "¿Qué dice el contrato de {p} sobre trabajos adicionales?", "cláusula de multas del contrato", "¿qué dice el contrato sobre fuerza mayor?",
        "condiciones del contrato de {p}", "¿el contrato reconoce el standby?", "retención de garantía en el contrato",
        "What does the {p} contract say about extra work?", "contract penalty clause", "force majeure terms in the contract",
        "does the contract cover standby costs", "O que diz o contrato do {p} sobre serviços adicionais?", "cláusula de multas", "força maior no contrato",
    ],
    "project_status": [
        "¿Cómo va {p}?", "estado de {p}", "resumen de {p}", "¿cómo está el proyecto {p}?", "dame el estado de {p}", "situación actual de {p}", "{p}",
        "How is {p} doing?", "status of {p}", "give me an update on {p}", "{p} summary", "Como está o {p}?", "situação do {p}", "resumo do {p}",
    ],
    "delays": [
        "¿Qué proyectos están atrasados?", "¿cuándo termina {p}?", "proyectos con atraso en {c}", "fecha de fin pronosticada de {p}",
        "¿vamos a terminar a tiempo?", "proyectos con SPI bajo", "¿cuántos meses de atraso tiene {p}?", "Which projects are behind schedule?",
        "when will {p} finish?", "delayed projects in {c}", "forecast finish date for {p}", "projects with low SPI", "Quais projetos estão atrasados?",
        "quando termina o {p}?", "previsão de término do {p}",
    ],
    "country_compare": [
        "¿Cómo se compara {c} con {c2}?", "rendimiento por país", "¿qué país tiene mejor margen?", "comparar países", "resultados por país",
        "¿cuál país tiene más órdenes pendientes?", "Compare {c} and {c2}", "performance by country", "which country has the best margin",
        "results by country", "Comparar {c} e {c2}", "desempenho por país", "qual país tem a melhor margem",
    ],
    "weld_quality": [
        "¿Cuál es la tasa de reparación de soldaduras?", "calidad de soldadura en {p}", "reparaciones de soldadura", "¿qué proyectos superan el 5% de reparaciones?",
        "rechazos de radiografía", "What is the weld repair rate?", "weld quality on {p}", "which projects exceed 5% weld repairs", "weld rejects",
        "Qual é a taxa de reparo de soldas?", "qualidade de solda no {p}",
    ],
    "top_risks": [
        "¿Qué proyectos están en riesgo?", "¿qué proyectos necesitan atención?", "proyectos en rojo", "alertas críticas", "¿qué debería preocuparme?",
        "¿cuáles son los principales riesgos?", "Which projects are at risk?", "what needs my attention", "red projects", "critical alerts",
        "top risks in the portfolio", "Quais projetos estão em risco?", "o que precisa da minha atenção", "alertas críticos",
        "proyectos en estado crítico", "¿qué proyectos van mal?", "which projects are in trouble", "projects in critical condition", "quais projetos vão mal", "obras em situação crítica",
    ],
    "activity_costs": [
        "¿Qué actividades tienen más sobrecosto?", "costos por actividad de {p}", "¿cuánto llevamos gastado en {a}?", "desviación por actividad",
        "¿en qué partidas nos pasamos?", "Which activities overrun the most?", "cost by activity for {p}", "how much have we spent on {a}",
        "variance by activity", "Quais atividades têm mais sobrecusto?", "custos por atividade do {p}", "quanto gastamos em {a}",
        "partidas con sobrecosto en {p}", "line items over budget on {p}", "cost items with the biggest variance", "itens de custo acima do orçamento no {p}",
    ],
    "lessons": [
        "lecciones aprendidas en {t}", "¿qué aprendimos de los proyectos cerrados?", "lecciones de proyectos anteriores",
        "¿qué recomendaciones dejaron los informes de cierre?", "errores que no debemos repetir", "lessons learned in {t}",
        "what did we learn from past projects", "close-out recommendations", "lições aprendidas na {t}", "o que aprendemos dos projetos encerrados",
    ],
    "project_list": [
        "¿Cuántos proyectos tenemos en {c}?", "lista de proyectos activos", "¿qué proyectos hay en {t}?", "proyectos cerrados", "¿qué proyectos tenemos?",
        "proyectos de ductos en {c}", "How many projects do we have in {c}?", "list active projects", "which projects are in {t}", "closed projects",
        "what projects do we have", "Quantos projetos temos no {c}?", "lista de projetos ativos", "projetos encerrados",
        "muéstrame los proyectos cerrados", "show me the active pipelines", "mostre os dutos encerrados", "inventario de proyectos", "project list",
    ],
    "anomalies": [
        "¿Hay costos anómalos?", "gastos sin avance", "¿dónde estamos pagando sin avanzar?", "anomalías en los costos de {p}", "costos inusuales este mes",
        "Are there cost anomalies?", "spending without progress", "unusual costs on {p}", "Há custos anômalos?", "gastos sem avanço",
        "picos de gasto inusuales", "costos fuera de lo normal", "abnormal cost peaks", "custos fora do normal",
    ],
    "data_quality": [
        "¿Cuadra el ERP con el Excel?", "diferencias entre GP y el control de costos", "calidad de los datos", "¿hay inconsistencias en los informes?",
        "conciliación contable", "Does the ERP match the Excel?", "differences between GP and cost control", "data quality issues", "reconciliation with Dynamics",
        "O ERP bate com o Excel?", "diferenças entre o GP e o controle de custos", "qualidade dos dados",
    ],
    "general": [
        "¿Qué es {g}?", "¿qué significa {g}?", "explícame {g}", "define {g}", "¿para qué sirve {g}?", "¿cómo se calcula {g}?",
        "What is {g}?", "what does {g} mean?", "explain {g}", "how is {g} calculated?", "O que é {g}?", "o que significa {g}?", "explique {g}",
        "¿cómo funciona este sistema?", "¿de dónde vienen los datos?", "¿los datos son reales?", "¿qué tan preciso es?", "¿necesita internet?",
        "¿cómo subo un archivo?", "¿cuánto cuesta implementarlo?", "¿en qué idiomas funciona?", "¿qué es Conduto?",
        "how does this system work?", "where does the data come from?", "is this real data?", "how accurate is it?", "do you need internet?",
        "how do I upload a file?", "how long does it take to implement?", "como funciona o sistema?", "de onde vêm os dados?", "os dados são reais?",
    ],
    "document_search": [
        "busca en los documentos {k}", "¿qué dicen los informes sobre {k}?", "muéstrame el informe de {p} de mayo", "documentos sobre deslizamiento en {p}",
        "¿dónde se menciona el río Coca?", "search documents for {k}", "what do the reports say about {k}", "show me the monthly report for {p}",
        "procure nos documentos {k}", "o que dizem os relatórios sobre {k}",
    ],
}

# Written by hand; not generated from the templates.
TEST_SET = [
    ("¿Me das un panorama general de las obras?", "portfolio_summary"), ("Big picture: how are we doing overall?", "portfolio_summary"), ("Visão geral da carteira, por favor", "portfolio_summary"),
    ("¿En qué proyectos el costo real supera lo previsto?", "overruns"), ("Which jobs are burning more money than budgeted?", "overruns"), ("Tem obra estourando o orçamento?", "overruns"),
    ("explícame la caída de margen del Tramo B", "margin_project"), ("How did Litoral Norte lose margin?", "margin_project"), ("margem do Selva Central", "margin_project"),
    ("¿cuánto dinero está atrapado en adicionales sin aprobar?", "pending_cos"), ("list the change orders still waiting for the client", "pending_cos"), ("quanto falta aprovar de ordens de alteração no Brasil", "pending_cos"),
    ("precio promedio por kilómetro en la sierra", "benchmark"), ("typical cost of one kilometre in the jungle", "benchmark"), ("quanto custa em média o km no litoral", "benchmark"),
    ("¿cuánto tiempo perdimos por lluvias el último año?", "lost_days"), ("how many days were lost to protests?", "lost_days"), ("dias parados por chuvas", "lost_days"),
    ("¿el contrato del Ducto Selva Central tiene multas por atraso?", "contract"), ("what are the delay penalties in the contract?", "contract"), ("o contrato prevê multa por atraso?", "contract"),
    ("¿qué tal va Litoral Norte?", "project_status"), ("update me on EC-2511", "project_status"), ("como anda o Serra do Mar?", "project_status"),
    ("¿cuál proyecto tiene más retraso?", "delays"), ("are we going to finish Selva Central on time?", "delays"), ("qual obra está mais atrasada?", "delays"),
    ("¿Perú o Ecuador, quién tiene mejor rentabilidad?", "country_compare"), ("how does Brazil stack up against Peru?", "country_compare"), ("comparativo entre países", "country_compare"),
    ("¿cómo están las reparaciones de soldadura en el Tramo B?", "weld_quality"), ("weld repair percentage by project", "weld_quality"), ("índice de reparo de solda", "weld_quality"),
    ("¿cuáles son los proyectos críticos?", "top_risks"), ("what should keep me up at night?", "top_risks"), ("quais obras estão no vermelho?", "top_risks"),
    ("¿en qué actividades se va la plata en EC-2503?", "activity_costs"), ("which cost items are over budget on PE-2410?", "activity_costs"), ("em quais atividades estouramos o orçamento?", "activity_costs"),
    ("¿qué lecciones nos dejaron los proyectos en la selva?", "lessons"), ("lessons from mountain projects", "lessons"), ("aprendizados dos projetos passados", "lessons"),
    ("¿cuántas obras activas hay en Brasil?", "project_list"), ("show me all closed pipelines", "project_list"), ("quais projetos existem no Peru?", "project_list"),
    ("¿hay meses donde gastamos sin avanzar?", "anomalies"), ("find strange spending spikes", "anomalies"), ("gastos fora do padrão", "anomalies"),
    ("¿los números del GP coinciden con los del Excel?", "data_quality"), ("is there any mismatch between the ledger and project control?", "data_quality"), ("inconsistências nos dados", "data_quality"),
    ("hola, ¿qué sabes hacer?", "general"), ("thank you!", "general"), ("bom dia", "general"),
    ("busca en los informes algo sobre el río Payamino", "document_search"), ("find documents mentioning slope stabilization", "document_search"), ("procure relatórios sobre a manta termocontrátil", "document_search"),
    # added after the template review, never tuned against
    ("¿qué obras me deberían preocupar este mes?", "top_risks"), ("dime qué partidas del Selva Central se desviaron", "activity_costs"),
    ("enumera los proyectos terminados", "project_list"), ("¿detectaste gastos raros en Litoral Norte?", "anomalies"),
    ("how much will EC-2503 cost at completion?", "project_status"), ("¿qué dice el informe de cierre sobre geotecnia?", "lessons"),
    ("compare the three countries by margin", "country_compare"), ("¿cuánto nos falta cobrar por adicionales en Perú?", "pending_cos"),
    ("¿qué quiere decir eficiencia de plazo?", "general"), ("what exactly is earned value?", "general"),
    ("o que é uma ordem de alteração?", "general"), ("¿estos números son de verdad?", "general"),
]

PREFIX = ["", "", "", "oye ", "por favor ", "dime ", "quisiera saber ", "can you tell me ", "please ", "me diz ", "quero saber "]


def _fill(tpl: str, rng: random.Random) -> str:
    c1, c2 = rng.sample(C, 2)
    return tpl.format(p=rng.choice(P), c=c1, c2=c2, t=rng.choice(T), k=rng.choice(K), a=rng.choice(A), g=rng.choice(G))


def project_index() -> ProjectIndex:
    return ProjectIndex([(p["code"], p["name"]) for p in PROJECTS])


def training_data(index: ProjectIndex, seed: int = 11, per_tpl: int = 6) -> tuple[list[str], list[str]]:
    rng = random.Random(seed)
    X, y = [], []
    for intent, tpls in TEMPLATES.items():
        for tpl in tpls:
            n = per_tpl if "{" in tpl else 3
            for _ in range(n):
                q = rng.choice(PREFIX) + _fill(tpl, rng)
                if rng.random() < 0.3:
                    q = q.lower()
                X.append(mask(q, extract(q, index)))
                y.append(intent)
    return X, y


def train():
    index = project_index()
    X, y = training_data(index)
    model = make_pipeline(
        make_union(
            TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True),
            TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True),
        ),
        LogisticRegression(C=8, max_iter=4000, class_weight="balanced"),
    )
    model.fit(X, y)
    qs = [q for q, _ in TEST_SET]
    truth = [t for _, t in TEST_SET]
    pred = [str(p) for p in model.predict([mask(q, extract(q, index)) for q in qs])]
    metrics = dict(
        name="intent_classifier", algorithm="TF-IDF (words + char 3-5 grams) + logistic regression, entities masked",
        n_train=len(X), n_test=len(TEST_SET), classes=len(TEMPLATES), languages=["es", "en", "pt"],
        accuracy=sum(p == t for p, t in zip(pred, truth)) / len(truth),
        errors=[dict(question=q, expected=t, predicted=p) for q, t, p in zip(qs, truth, pred) if p != t],
    )
    return model, metrics


def classify(model, index: ProjectIndex, question: str) -> dict:
    ents = extract(question, index)
    masked = mask(question, ents)
    proba = model.predict_proba([masked])[0]
    classes = [str(c) for c in model.classes_]
    order = proba.argsort()[::-1]
    return dict(intent=classes[order[0]], confidence=round(float(proba[order[0]]), 3),
                alternatives=[(classes[i], round(float(proba[i]), 3)) for i in order[1:3]], entities=ents, masked=masked)
