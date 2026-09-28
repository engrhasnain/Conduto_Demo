"""Connectors: how the system reads the programs Conduto already uses.

The catalog describes every connector (what it reads, how, how often, and how its records map to the common
model). Three are live in the demo and really read something:

- files: the project folders (Excel, Microsoft Project, PDF) — scans the folders and reports files waiting for review;
- dynamics_gp: the accounting exports — re-reads the transactions and re-runs the accounting-vs-Excel reconciliation;
- sales: the sales system (opportunities) — reads a simulated Dynamics 365 Sales response, keeps a snapshot of what it
  received (so every figure is traceable to a row) and inserts or updates the opportunities.

The others are "available" (would be switched on in the pilot or after the accounting-system decision) or "planned".
Scheduled runs are simulated relative to the current time so the demo never looks stale.
"""
import json
import time
from datetime import datetime, timedelta, timezone

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import DATA_DIR, INBOX_DIR, SOURCES_DIR, STATUS_PERIOD
from ..models import Document, ErpTransaction, FxRate, IngestionJob, Opportunity, SyncRun

SALES_SOURCE = DATA_DIR / "connectors" / "dynamics365_sales_opportunities.json"  # stands in for the live system
SNAPSHOT_DIR = SOURCES_DIR / "_SALES"
SNAPSHOT_SHEET = "Oportunidades"
SNAPSHOT_COLUMNS = [
    ("crm_id", "Id"), ("name", "Nombre"), ("client", "Cliente"), ("country", "País"), ("kind", "Tipo"), ("terrain", "Terreno"),
    ("region", "Región"), ("diameter_in", "Diámetro (pulgadas)"), ("length_km", "Longitud (km)"), ("stage", "Etapa"),
    ("currency", "Moneda"), ("value", "Valor"), ("bid_margin_pct", "Margen planificado"), ("probability", "Probabilidad"),
    ("expected_decision", "Decisión esperada"), ("owner", "Responsable"), ("next_step_es", "Próximo paso"),
    ("project_code", "Proyecto"), ("lost_reason", "Motivo de pérdida"), ("modified_on", "Modificado"),
]
VALUE_COL = "L"  # column of "Valor": the cell every opportunity is traced to


def tx(es: str, en: str, pt: str) -> dict:
    return {"es": es, "en": en, "pt": pt}


CATALOG = [
    dict(
        key="files", name="SharePoint / OneDrive", category="files", status="connected", direction="in", every_minutes=15, phase="today",
        summary=tx("Lee las carpetas de cada proyecto: controles de costos en Excel, cronogramas de Microsoft Project y contratos, órdenes de cambio e informes en PDF.",
                   "Reads each project's folders: cost control in Excel, Microsoft Project schedules, and contracts, change orders and reports in PDF.",
                   "Lê as pastas de cada projeto: controle de custos em Excel, cronogramas do Microsoft Project e contratos, ordens de alteração e relatórios em PDF."),
        reads=[tx("Controles de costos (Excel)", "Cost control workbooks (Excel)", "Controles de custos (Excel)"),
               tx("Cronogramas (Microsoft Project)", "Schedules (Microsoft Project)", "Cronogramas (Microsoft Project)"),
               tx("Contratos, órdenes de cambio e informes (PDF)", "Contracts, change orders and reports (PDF)", "Contratos, ordens de alteração e relatórios (PDF)")],
        method=tx("Revisa las carpetas cada 15 minutos. Los archivos nuevos o modificados pasan a «Cargar datos», donde una persona los revisa antes de guardarlos.",
                  "Checks the folders every 15 minutes. New or changed files go to “Load data”, where a person reviews them before they are saved.",
                  "Verifica as pastas a cada 15 minutos. Arquivos novos ou alterados vão para «Carregar dados», onde uma pessoa os revisa antes de salvar."),
        mapping=[(tx("Fila de costo del Excel", "Cost row in the Excel file", "Linha de custo do Excel"), tx("Costo real por proyecto, actividad y mes", "Actual cost by project, activity and month", "Custo real por projeto, atividade e mês")),
                 (tx("Tarea del cronograma", "Schedule task", "Tarefa do cronograma"), tx("Tarea con fechas planificadas y reales", "Task with planned and actual dates", "Tarefa com datas previstas e reais")),
                 (tx("Orden de cambio en PDF", "Change order PDF", "Ordem de alteração em PDF"), tx("Orden de cambio con monto, causa y estado", "Change order with amount, cause and status", "Ordem de alteração com valor, causa e situação"))],
        setup=[tx("Una cuenta de solo lectura en SharePoint o OneDrive", "A read-only account in SharePoint or OneDrive", "Uma conta somente leitura no SharePoint ou OneDrive"),
               tx("La lista de carpetas de proyecto por país", "The list of project folders per country", "A lista de pastas de projeto por país")],
    ),
    dict(
        key="dynamics_gp", name="Microsoft Dynamics GP", category="accounting", status="connected", direction="in", every_minutes=1440, phase="today",
        summary=tx("Trae los movimientos contables de cada proyecto y los compara con el Excel de control de costos.",
                   "Brings each project's accounting entries and compares them with the cost-control Excel.",
                   "Traz os lançamentos contábeis de cada projeto e os compara com o Excel de controle de custos."),
        reads=[tx("Movimientos del libro mayor con cuenta de proyecto", "General-ledger entries with a project account", "Lançamentos do razão com conta de projeto"),
               tx("Facturas y proveedores", "Invoices and vendors", "Faturas e fornecedores")],
        method=tx("Hoy: una exportación diaria programada desde SmartList de Dynamics GP. En el piloto: consulta directa de solo lectura a la base de datos contable.",
                  "Today: a scheduled daily export from Dynamics GP SmartList. In the pilot: a direct read-only query to the accounting database.",
                  "Hoje: uma exportação diária programada do SmartList do Dynamics GP. No piloto: consulta direta somente leitura ao banco de dados contábil."),
        mapping=[(tx("Movimiento contable con cuenta de proyecto", "Accounting entry with a project account", "Lançamento contábil com conta de projeto"), tx("Costo contable por proyecto, mes y tipo de costo", "Accounting cost by project, month and cost type", "Custo contábil por projeto, mês e tipo de custo")),
                 (tx("Factura de proveedor", "Vendor invoice", "Fatura de fornecedor"), tx("Referencia para rastrear cada diferencia con el Excel", "Reference to trace each difference with the Excel", "Referência para rastrear cada diferença com o Excel"))],
        setup=[tx("Un reporte SmartList programado por país (o un usuario de solo lectura en la base de datos)", "A scheduled SmartList report per country (or a read-only database user)", "Um relatório SmartList programado por país (ou um usuário somente leitura no banco)"),
               tx("La regla que indica qué segmento de la cuenta es el proyecto", "The rule saying which account segment is the project", "A regra que indica qual segmento da conta é o projeto")],
    ),
    dict(
        key="sales", name="Dynamics 365 Sales", category="sales", status="connected", direction="in", every_minutes=60, phase="today",
        summary=tx("Trae las oportunidades comerciales (ofertas en preparación, presentadas y ganadas) y revisa cada oferta abierta contra lo que realmente costaron obras parecidas.",
                   "Brings the commercial opportunities (bids being prepared, submitted and won) and checks every open bid against what similar jobs really cost.",
                   "Traz as oportunidades comerciais (propostas em preparação, apresentadas e ganhas) e confere cada proposta aberta contra o que obras parecidas realmente custaram."),
        reads=[tx("Oportunidades: cliente, alcance, valor y margen planificado", "Opportunities: client, scope, value and planned margin", "Oportunidades: cliente, escopo, valor e margem planejada"),
               tx("Etapa, probabilidad y fecha esperada de decisión", "Stage, probability and expected decision date", "Etapa, probabilidade e data prevista de decisão"),
               tx("Responsable y próximo paso", "Owner and next step", "Responsável e próximo passo")],
        method=tx("Conexión directa de solo lectura, cada hora. Cada lectura guarda una copia de lo recibido, así cada cifra se puede rastrear hasta su fila.",
                  "Direct read-only connection, every hour. Each read keeps a copy of what was received, so every figure can be traced to its row.",
                  "Conexão direta somente leitura, a cada hora. Cada leitura guarda uma cópia do que foi recebido, assim cada número pode ser rastreado até sua linha."),
        mapping=[(tx("Oportunidad abierta", "Open opportunity", "Oportunidade aberta"), tx("Oferta en curso, revisada contra el histórico", "Bid in progress, checked against history", "Proposta em andamento, conferida com o histórico")),
                 (tx("Oportunidad ganada", "Won opportunity", "Oportunidade ganha"), tx("Proyecto (enlazado por su código)", "Project (linked by its code)", "Projeto (vinculado pelo código)")),
                 (tx("Oportunidad perdida", "Lost opportunity", "Oportunidade perdida"), tx("Motivo de pérdida, para aprender de él", "Reason for losing, to learn from it", "Motivo da perda, para aprender com ele"))],
        setup=[tx("Un usuario de solo lectura en el sistema comercial", "A read-only user in the sales system", "Um usuário somente leitura no sistema comercial"),
               tx("Tres campos en cada oportunidad: diámetro, longitud y terreno", "Three fields on each opportunity: diameter, length and terrain", "Três campos em cada oportunidade: diâmetro, comprimento e terreno")],
        note=tx("Por confirmar en el diagnóstico: qué sistema comercial usa Conduto. El mismo conector sirve para Dynamics 365 Sales, Salesforce, HubSpot o una hoja de cálculo compartida.",
                "To confirm during discovery: which sales system Conduto uses. The same connector works for Dynamics 365 Sales, Salesforce, HubSpot or a shared spreadsheet.",
                "A confirmar no diagnóstico: qual sistema comercial a Conduto usa. O mesmo conector serve para Dynamics 365 Sales, Salesforce, HubSpot ou uma planilha compartilhada."),
    ),
    dict(
        key="sap", name="SAP S/4HANA", category="accounting", status="available", direction="in", every_minutes=1440, phase="after_decision",
        summary=tx("Si Conduto elige SAP, este conector reemplaza al de Dynamics GP. Los tableros y los indicadores no cambian.",
                   "If Conduto chooses SAP, this connector replaces the Dynamics GP one. Dashboards and indicators stay the same.",
                   "Se a Conduto escolher SAP, este conector substitui o do Dynamics GP. Os painéis e indicadores não mudam."),
        reads=[tx("Estructura de cada proyecto y sus elementos de costo", "Each project's structure and cost elements", "Estrutura de cada projeto e seus elementos de custo"),
               tx("Costos contabilizados y órdenes de compra", "Posted costs and purchase orders", "Custos contabilizados e pedidos de compra")],
        method=tx("Servicios de consulta estándar de SAP, con un usuario de solo lectura.", "SAP's standard query services, with a read-only user.", "Serviços de consulta padrão do SAP, com um usuário somente leitura."),
        mapping=[(tx("Costo contabilizado por elemento de proyecto", "Posted cost by project element", "Custo contabilizado por elemento de projeto"), tx("Costo contable por proyecto, mes y tipo de costo", "Accounting cost by project, month and cost type", "Custo contábil por projeto, mês e tipo de custo"))],
        setup=[tx("La decisión del nuevo sistema contable", "The decision on the new accounting system", "A decisão do novo sistema contábil"),
               tx("Un usuario de solo lectura en SAP", "A read-only user in SAP", "Um usuário somente leitura no SAP"),
               tx("La tabla de equivalencias entre cuentas de Dynamics GP y SAP, para no perder el histórico", "The mapping between Dynamics GP and SAP accounts, to keep the history", "A tabela de equivalências entre contas do Dynamics GP e do SAP, para manter o histórico")],
    ),
    dict(
        key="d365_finance", name="Dynamics 365 Finance", category="accounting", status="available", direction="in", every_minutes=1440, phase="after_decision",
        summary=tx("Si Conduto elige Dynamics 365, este conector reemplaza al de Dynamics GP. Los tableros y los indicadores no cambian.",
                   "If Conduto chooses Dynamics 365, this connector replaces the Dynamics GP one. Dashboards and indicators stay the same.",
                   "Se a Conduto escolher Dynamics 365, este conector substitui o do Dynamics GP. Os painéis e indicadores não mudam."),
        reads=[tx("Proyectos y categorías de costo", "Projects and cost categories", "Projetos e categorias de custo"),
               tx("Movimientos contables y facturas de proveedores", "Accounting entries and vendor invoices", "Lançamentos contábeis e faturas de fornecedores")],
        method=tx("Servicios de datos estándar de Dynamics 365, con permisos de solo lectura.", "Dynamics 365 standard data services, with read-only permissions.", "Serviços de dados padrão do Dynamics 365, com permissões somente leitura."),
        mapping=[(tx("Movimiento de proyecto", "Project transaction", "Lançamento de projeto"), tx("Costo contable por proyecto, mes y tipo de costo", "Accounting cost by project, month and cost type", "Custo contábil por projeto, mês e tipo de custo"))],
        setup=[tx("La decisión del nuevo sistema contable", "The decision on the new accounting system", "A decisão do novo sistema contábil"),
               tx("Un usuario de solo lectura en Dynamics 365", "A read-only user in Dynamics 365", "Um usuário somente leitura no Dynamics 365")],
    ),
    dict(
        key="project_online", name="Microsoft Project Online", category="schedules", status="available", direction="in", every_minutes=60, phase="pilot",
        summary=tx("Lee los cronogramas directamente desde Project Online, sin tener que exportar archivos.", "Reads schedules directly from Project Online, with no files to export.", "Lê os cronogramas direto do Project Online, sem exportar arquivos."),
        reads=[tx("Tareas, fechas de línea base y reales, avance", "Tasks, baseline and actual dates, progress", "Tarefas, datas de linha de base e reais, avanço")],
        method=tx("Conexión directa de solo lectura a los proyectos publicados.", "Direct read-only connection to published projects.", "Conexão direta somente leitura aos projetos publicados."),
        mapping=[(tx("Tarea del proyecto publicado", "Task in a published project", "Tarefa do projeto publicado"), tx("Tarea con fechas planificadas y reales", "Task with planned and actual dates", "Tarefa com datas previstas e reais"))],
        setup=[tx("Confirmar si Conduto usa Project Online o solo archivos de escritorio", "Confirm whether Conduto uses Project Online or only desktop files", "Confirmar se a Conduto usa o Project Online ou só arquivos locais")],
    ),
    dict(
        key="primavera", name="Oracle Primavera P6", category="schedules", status="available", direction="in", every_minutes=1440, phase="pilot",
        summary=tx("Si un cliente o país exige Primavera, sus cronogramas se leen igual que los de Microsoft Project.", "If a client or country requires Primavera, its schedules are read just like Microsoft Project ones.", "Se um cliente ou país exigir Primavera, seus cronogramas são lidos como os do Microsoft Project."),
        reads=[tx("Actividades, fechas y avance", "Activities, dates and progress", "Atividades, datas e avanço")],
        method=tx("Archivos de exportación de Primavera o consulta de solo lectura a su base de datos.", "Primavera export files or a read-only query to its database.", "Arquivos de exportação do Primavera ou consulta somente leitura ao banco."),
        mapping=[(tx("Actividad de Primavera", "Primavera activity", "Atividade do Primavera"), tx("Tarea con fechas planificadas y reales", "Task with planned and actual dates", "Tarefa com datas previstas e reais"))],
        setup=[tx("Saber qué proyectos o clientes usan Primavera", "Know which projects or clients use Primavera", "Saber quais projetos ou clientes usam Primavera")],
    ),
    dict(
        key="email", name="Microsoft Outlook", category="email", status="available", direction="in", every_minutes=15, phase="pilot",
        summary=tx("Las órdenes de cambio e informes que llegan a un buzón de proyectos pasan directo a «Cargar datos».", "Change orders and reports sent to a project mailbox go straight to “Load data”.", "Ordens de alteração e relatórios enviados a uma caixa de projetos vão direto para «Carregar dados»."),
        reads=[tx("Archivos adjuntos (Excel, PDF, cronogramas)", "Attachments (Excel, PDF, schedules)", "Anexos (Excel, PDF, cronogramas)")],
        method=tx("Lectura de un buzón dedicado, con permisos solo sobre ese buzón.", "Reads one dedicated mailbox, with permissions on that mailbox only.", "Leitura de uma caixa dedicada, com permissões só nessa caixa."),
        mapping=[(tx("Adjunto de correo", "Email attachment", "Anexo de e-mail"), tx("Archivo en espera de revisión en «Cargar datos»", "File waiting for review in “Load data”", "Arquivo aguardando revisão em «Carregar dados»"))],
        setup=[tx("Un buzón dedicado (por ejemplo, proyectos@conduto)", "A dedicated mailbox (for example, projects@conduto)", "Uma caixa dedicada (por exemplo, projetos@conduto)")],
    ),
    dict(
        key="power_bi", name="Power BI", category="reporting", status="available", direction="out", every_minutes=1440, phase="pilot",
        summary=tx("Publica el modelo consolidado para que finanzas y gerencia armen sus propios reportes. Hoy se puede descargar el Excel consolidado.",
                   "Publishes the consolidated model so finance and management can build their own reports. Today the consolidated Excel can be downloaded.",
                   "Publica o modelo consolidado para que finanças e gerência montem seus próprios relatórios. Hoje é possível baixar o Excel consolidado."),
        reads=[tx("Envía: proyectos, costos, avance, órdenes de cambio, ofertas", "Sends: projects, costs, progress, change orders, bids", "Envia: projetos, custos, avanço, ordens de alteração, propostas")],
        method=tx("Actualización diaria de un conjunto de datos, con el origen de cada valor.", "Daily refresh of a dataset, with each value's source.", "Atualização diária de um conjunto de dados, com a origem de cada valor."),
        mapping=[(tx("Modelo común", "Common model", "Modelo comum"), tx("Tablas de Power BI listas para reportes", "Power BI tables ready for reports", "Tabelas do Power BI prontas para relatórios"))],
        setup=[tx("Un espacio de trabajo de Power BI de Conduto", "A Conduto Power BI workspace", "Um espaço de trabalho do Power BI da Conduto")],
    ),
    dict(
        key="field_app", name=tx("Partes diarios de obra", "Daily site reports", "Diários de obra"), category="field", status="planned", direction="in", every_minutes=60, phase="rollout",
        summary=tx("Una aplicación móvil para registrar avance, soldaduras y eventos en obra el mismo día, sin esperar el informe mensual en PDF.",
                   "A mobile app to record progress, welds and site events the same day, without waiting for the monthly PDF report.",
                   "Um aplicativo para registrar avanço, soldas e ocorrências no mesmo dia, sem esperar o relatório mensal em PDF."),
        reads=[tx("Avance diario, soldaduras y reparaciones, eventos con fotos", "Daily progress, welds and repairs, events with photos", "Avanço diário, soldas e reparos, ocorrências com fotos")],
        method=tx("Formularios simples en el teléfono del supervisor, que funcionan sin señal y se envían al volver a tenerla.", "Simple forms on the supervisor's phone that work offline and send when back in coverage.", "Formulários simples no celular do supervisor, que funcionam sem sinal e enviam quando voltar a ter."),
        mapping=[(tx("Parte diario", "Daily report", "Diário de obra"), tx("Avance, producción y eventos del día", "Progress, production and events of the day", "Avanço, produção e ocorrências do dia"))],
        setup=[tx("Elegir un proyecto piloto y sus supervisores", "Choose a pilot project and its supervisors", "Escolher um projeto piloto e seus supervisores")],
    ),
]
BY_KEY = {c["key"]: c for c in CATALOG}
STAGE_PROBABILITY = {"prospecting": 0.1, "preparing": 0.25, "submitted": 0.4, "negotiation": 0.6, "won": 1.0, "lost": 0.0}


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def fx_usd(db: Session, currency: str) -> float:
    if currency == "USD":
        return 1.0
    r = db.scalar(select(FxRate.usd_per_unit).where(FxRate.currency == currency, FxRate.period == STATUS_PERIOD))
    return r or 1.0


# ---------------------------------------------------------------- sales system

def write_sales_snapshot(db: Session, records: list[dict], when: datetime, origin: str = "seed") -> tuple[Document, dict]:
    """Keep a copy of what the sales system returned; every opportunity is traced to its value cell."""
    from ..seed.run import add_doc  # the same helper every source document goes through

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = when.strftime("%Y%m%d-%H%M%S")
    path = SNAPSHOT_DIR / f"Dynamics365Sales_Oportunidades_{stamp}.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = SNAPSHOT_SHEET
    ws.append([h for _, h in SNAPSHOT_COLUMNS])
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F3A5F")
    locs = {}
    for i, r in enumerate(records, start=2):
        ws.append([r.get(k) for k, _ in SNAPSHOT_COLUMNS])
        locs[r["crm_id"]] = f"{SNAPSHOT_SHEET}!{VALUE_COL}{i}"
    for col, width in zip("ABCDEFGHIJKLMNOPQRST", (15, 42, 26, 6, 9, 11, 22, 10, 10, 12, 7, 15, 10, 10, 11, 22, 48, 10, 12, 12)):
        ws.column_dimensions[col].width = width
    wb.save(path)
    title = f"Dynamics 365 Sales – oportunidades ({when:%Y-%m-%d %H:%M} UTC)"
    doc = add_doc(db, None, "sales_export", title, path, "es", period=STATUS_PERIOD, origin=origin)
    return doc, locs


FIELDS = ("name", "client", "kind", "terrain", "region", "diameter_in", "length_km", "stage", "currency", "value", "bid_margin_pct",
          "probability", "expected_decision", "owner", "next_step_es", "next_step_en", "next_step_pt", "project_code", "lost_reason",
          "modified_on")
TRACKED = ("stage", "value", "bid_margin_pct", "probability", "expected_decision", "project_code", "lost_reason")


def upsert_opportunities(db: Session, records: list[dict], doc: Document, locs: dict) -> tuple[int, int, list[dict]]:
    existing = {o.crm_id: o for o in db.scalars(select(Opportunity))}
    new = updated = 0
    changes = []
    for r in records:
        o = existing.get(r["crm_id"])
        values = {k: r.get(k) for k in FIELDS}
        if o is None:
            db.add(Opportunity(crm_id=r["crm_id"], country_code=r["country"], document_id=doc.id, locator=locs[r["crm_id"]], **values))
            new += 1
            changes.append(dict(crm_id=r["crm_id"], name=r["name"], kind="new"))
            continue
        diff = [(k, getattr(o, k), values[k]) for k in TRACKED if getattr(o, k) != values[k]]
        for k, v in values.items():
            setattr(o, k, v)
        o.country_code, o.document_id, o.locator = r["country"], doc.id, locs[r["crm_id"]]
        if diff:
            updated += 1
            changes.append(dict(crm_id=r["crm_id"], name=r["name"], kind="updated", currency=r["currency"],
                                fields=[dict(field=k, old=a, new=b) for k, a, b in diff]))
    db.flush()
    return new, updated, changes


def read_sales_source() -> list[dict]:
    return json.loads(SALES_SOURCE.read_text(encoding="utf-8"))["value"]


def _sync_sales(db: Session, when: datetime) -> dict:
    records = read_sales_source()
    current = {o.crm_id: o for o in db.scalars(select(Opportunity))}
    changed = any(r["crm_id"] not in current or any(getattr(current[r["crm_id"]], k) != r.get(k) for k in TRACKED) for r in records)
    if changed:  # keep a new copy only when something changed
        doc, locs = write_sales_snapshot(db, records, when, origin="connector")
        new, updated, changes = upsert_opportunities(db, records, doc, locs)
    else:
        doc = db.get(Document, next(iter(current.values())).document_id) if current else None
        new, updated, changes = 0, 0, []
    return dict(read=len(records), new=new, updated=updated, issues=0, status="ok", document_id=doc.id if doc else None,
                details=dict(changes=changes))


# ---------------------------------------------------------------- files and accounting

def _project_files() -> list:
    return [p for p in SOURCES_DIR.rglob("*") if p.is_file() and not p.parent.name.startswith("_")]


def waiting_files(db: Session) -> list[str]:
    done = {j.filename for j in db.scalars(select(IngestionJob).where(IngestionJob.status == "imported"))}
    return sorted(p.name for p in INBOX_DIR.iterdir() if p.is_file() and p.name not in done) if INBOX_DIR.exists() else []


def _sync_files(db: Session, when: datetime) -> dict:
    files = _project_files()
    known = {d.filename for d in db.scalars(select(Document))}
    waiting = waiting_files(db)
    new_files = [p.name for p in files if p.name not in known]
    folders = len({p.parent for p in files})
    return dict(read=len(files) + len(waiting), new=len(new_files), updated=0, issues=len(waiting),
                status="attention" if waiting else "ok", details=dict(folders=folders, waiting=waiting))


def _sync_gp(db: Session, when: datetime) -> dict:
    from .reconciliation import reconcile

    n = db.scalar(select(func.count()).select_from(ErpTransaction)) or 0
    exports = db.scalar(select(func.count()).select_from(Document).where(Document.doc_type == "erp_export")) or 0
    rec = reconcile(db)
    diffs = len(rec["discrepancies"])
    return dict(read=n, new=0, updated=0, issues=diffs, status="attention" if diffs else "ok",
                details=dict(exports=exports, matched=rec["matched"], cells=rec["cells"], differences=diffs))


SYNC = {"files": _sync_files, "dynamics_gp": _sync_gp, "sales": _sync_sales}


class ConnectorError(RuntimeError):
    pass


def sync(db: Session, key: str) -> dict:
    c = BY_KEY.get(key)
    if not c:
        raise ConnectorError("unknown")
    if c["status"] != "connected":
        raise ConnectorError("not_connected")
    when, t0 = now(), time.perf_counter()
    res = SYNC[key](db, when)
    run = SyncRun(connector=key, trigger="manual", started_at=when, duration_ms=int((time.perf_counter() - t0) * 1000) + 1,
                  status=res["status"], records_read=res["read"], records_new=res["new"], records_updated=res["updated"],
                  issues=res["issues"], details=res.get("details"), document_id=res.get("document_id"))
    db.add(run)
    db.commit()
    if key == "sales":
        from .search import invalidate
        invalidate()
    return run_dict(run, now())


def test_connection(db: Session, key: str) -> dict:
    c = BY_KEY.get(key)
    if not c or c["status"] != "connected":
        raise ConnectorError("not_connected")
    t0 = time.perf_counter()
    if key == "files":
        files = _project_files()
        detail = dict(folders=len({p.parent for p in files}), files=len(files))
    elif key == "dynamics_gp":
        exports = list((SOURCES_DIR / "_ERP").glob("*.xlsx"))
        detail = dict(exports=len(exports), latest=STATUS_PERIOD)
    else:
        detail = dict(records=len(read_sales_source()))
    return dict(ok=True, key=key, ms=int((time.perf_counter() - t0) * 1000) + 1, details=detail)


# ---------------------------------------------------------------- reading the catalog

def run_dict(r: SyncRun, ref: datetime) -> dict:
    at = r.started_at if r.offset_minutes is None else ref.replace(microsecond=0) - timedelta(minutes=r.offset_minutes)
    return dict(id=r.id, trigger=r.trigger, at=at.isoformat() + "Z", duration_ms=r.duration_ms, status=r.status,
                read=r.records_read, new=r.records_new, updated=r.records_updated, issues=r.issues,
                details=r.details or {}, document_id=r.document_id)


def _runs(db: Session, key: str, ref: datetime, limit: int = 12) -> list[dict]:
    runs = [run_dict(r, ref) for r in db.scalars(select(SyncRun).where(SyncRun.connector == key))]
    return sorted(runs, key=lambda x: x["at"], reverse=True)[:limit]


def _records(db: Session, key: str) -> int:
    if key == "files":
        return db.scalar(select(func.count()).select_from(Document).where(Document.doc_type.not_in(("erp_export", "sales_export")))) or 0
    if key == "dynamics_gp":
        return db.scalar(select(func.count()).select_from(ErpTransaction)) or 0
    if key == "sales":
        return db.scalar(select(func.count()).select_from(Opportunity)) or 0
    return 0


def _public(c: dict) -> dict:
    out = {k: v for k, v in c.items() if k != "mapping"}
    out["mapping"] = [dict(source=s, target=t) for s, t in c["mapping"]]
    if isinstance(out["name"], str):
        out["name"] = tx(out["name"], out["name"], out["name"])
    return out


def list_connectors(db: Session) -> dict:
    ref = now()
    items = []
    for c in CATALOG:
        item = _public(c)
        runs = _runs(db, c["key"], ref, limit=1) if c["status"] == "connected" else []
        last = runs[0] if runs else None
        item.update(records=_records(db, c["key"]) if c["status"] == "connected" else 0, last_run=last)
        if last:
            since = (ref - datetime.fromisoformat(last["at"].rstrip("Z"))).total_seconds() / 60
            item["next_in_minutes"] = max(int(c["every_minutes"] - since), 0)
        items.append(item)
    connected = [i for i in items if i["status"] == "connected"]
    return dict(
        now=ref.isoformat() + "Z",
        connectors=items,
        summary=dict(connected=len(connected), available=sum(1 for i in items if i["status"] == "available"),
                     planned=sum(1 for i in items if i["status"] == "planned"),
                     records=sum(i["records"] for i in connected),
                     attention=sum((i["last_run"] or {}).get("issues", 0) for i in connected),
                     waiting_files=len(waiting_files(db))),
    )


def connector_detail(db: Session, key: str) -> dict | None:
    c = BY_KEY.get(key)
    if not c:
        return None
    ref = now()
    item = _public(c)
    item.update(records=_records(db, key) if c["status"] == "connected" else 0,
                runs=_runs(db, key, ref) if c["status"] == "connected" else [], now=ref.isoformat() + "Z")
    return item
