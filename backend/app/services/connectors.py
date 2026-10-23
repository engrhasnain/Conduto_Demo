"""Connectors: how the system reads the programs Montamar already uses.

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
        key="bejerman", name="Bejerman", category="accounting", status="connected", direction="out", every_minutes=60, phase="today",
        summary=tx("Carga las facturas de proveedor en Bejerman, ya leidas y verificadas, sin tocar la conexion del estudio contable.",
                   "Posts supplier invoices into Bejerman, already read and checked, without touching the external accountant's connection.",
                   "Lanca as faturas de fornecedor no Bejerman, ja lidas e verificadas, sem mexer na conexao do escritorio contabil."),
        reads=[tx("Proveedores y su CUIT", "Vendors and their tax number", "Fornecedores e seu CNPJ"),
               tx("Comprobantes ya registrados, para no cargar dos veces", "Documents already posted, so nothing is entered twice", "Documentos ja lancados, para nao lancar duas vezes"),
               tx("Plan de cuentas y centros de costo", "Chart of accounts and cost centres", "Plano de contas e centros de custo")],
        method=tx("Dos caminos, segun lo que permita la instalacion. Si hay interfaz de importacion o base accesible, se escribe por ahi. Si no la hay, el sistema carga la factura por la misma pantalla que usa una persona, campo por campo, y vuelve a leer lo guardado para confirmar que entro completo. En los dos casos escribe solo lo que una persona aprobo.",
                  "Two routes, depending on what the installation allows. If there is an import interface or a reachable database, it writes through that. If there is not, the system enters the invoice through the same screen a person uses, field by field, then reads back what was saved to confirm it went in whole. Either way it only writes what a person approved.",
                  "Dois caminhos, conforme o que a instalacao permitir. Se houver interface de importacao ou banco acessivel, grava por ali. Se nao houver, o sistema lanca a fatura pela mesma tela que uma pessoa usa, campo a campo, e rele o que foi salvo para confirmar que entrou inteiro. Nos dois casos grava apenas o que uma pessoa aprovou."),
        mapping=[(tx("Factura A, B o C recibida", "Factura A, B or C received", "Fatura A, B ou C recebida"),
                  tx("Comprobante de compra con su CAE y su tipo", "Purchase document with its authorisation code and type", "Documento de compra com seu codigo de autorizacao e tipo")),
                 (tx("CUIT del emisor", "Issuer tax number", "CNPJ do emissor"),
                  tx("Proveedor del maestro de Bejerman", "Vendor in the Bejerman master file", "Fornecedor no cadastro do Bejerman")),
                 (tx("Neto, IVA y percepciones", "Net, VAT and perceptions", "Liquido, IVA e percepcoes"),
                  tx("Renglones contables con su cuenta", "Accounting lines with their account", "Linhas contabeis com sua conta")),
                 (tx("Orden de compra y remito", "Purchase order and delivery note", "Ordem de compra e remessa"),
                  tx("Imputacion a la obra y al centro de costo", "Allocation to the job and cost centre", "Alocacao a obra e centro de custo"))],
        setup=[tx("Confirmar si esta instalacion de Bejerman tiene interfaz de importacion o base accesible", "Confirm whether this Bejerman installation has an import interface or a reachable database", "Confirmar se esta instalacao do Bejerman tem interface de importacao ou banco acessivel"),
               tx("Un usuario propio para el sistema, con permiso de carga y no de modificacion", "A dedicated user for the system, allowed to enter documents but not to change them", "Um usuario proprio para o sistema, com permissao de lancamento e nao de alteracao"),
               tx("El plan de cuentas y la regla de imputacion por tipo de gasto", "The chart of accounts and the rule for allocating each kind of spend", "O plano de contas e a regra de imputacao por tipo de gasto")],
        note=tx("Por confirmar en el diagnostico: si Bejerman expone una interfaz de importacion. No hace falta saberlo para empezar, el segundo camino funciona igual y es el que se muestra aca. Lo que no cambia en ninguno de los dos casos: el sistema no modifica ni borra nada de lo que ya esta cargado, asi que la conexion con el estudio contable queda intacta.",
                "To confirm during discovery: whether Bejerman exposes an import interface. It is not needed to start - the second route works either way, and it is the one shown here. What does not change in either case: the system never alters or deletes anything already posted, so the external accountant's connection is untouched.",
                "A confirmar no diagnostico: se o Bejerman expoe uma interface de importacao. Nao e necessario para comecar, o segundo caminho funciona de qualquer forma e e o mostrado aqui. O que nao muda em nenhum dos casos: o sistema nao altera nem apaga nada ja lancado, entao a conexao com o escritorio contabil fica intacta."),
    ),
    dict(
        key="dynamics_gp", name="Bejerman (lectura)", category="accounting", status="connected", direction="in", every_minutes=1440, phase="today",
        summary=tx("Lee lo que ya esta registrado en la contabilidad y lo compara con el control de costos en Excel, obra por obra.",
                   "Reads what is already posted in the accounts and compares it with the cost control in Excel, job by job.",
                   "Le o que ja esta lancado na contabilidade e compara com o controle de custos em Excel, obra por obra."),
        reads=[tx("Movimientos contables con imputacion a obra", "Accounting entries allocated to a job", "Lancamentos contabeis alocados a obra"),
               tx("Facturas de proveedores ya registradas", "Supplier invoices already posted", "Faturas de fornecedores ja lancadas")],
        method=tx("Solo lectura. Hoy: una exportacion diaria. En el piloto: consulta directa de solo lectura. El sistema nunca escribe por este camino; para cargar usa el conector de arriba, y solo lo aprobado.",
                  "Read only. Today: a daily export. In the pilot: a direct read-only query. The system never writes through this route; to post it uses the connector above, and only what was approved.",
                  "Somente leitura. Hoje: uma exportacao diaria. No piloto: consulta direta somente leitura. O sistema nunca grava por este caminho; para lancar usa o conector acima, e apenas o aprovado."),
        mapping=[(tx("Movimiento contable con imputacion a obra", "Accounting entry allocated to a job", "Lancamento contabil alocado a obra"),
                  tx("Costo contable por obra, mes y tipo de costo", "Accounting cost by job, month and cost type", "Custo contabil por obra, mes e tipo de custo")),
                 (tx("Factura de proveedor", "Supplier invoice", "Fatura de fornecedor"),
                  tx("Referencia para rastrear cada diferencia con el Excel", "Reference to trace each difference against the Excel", "Referencia para rastrear cada diferenca com o Excel"))],
        setup=[tx("Un usuario de solo lectura, o una exportacion programada", "A read-only user, or a scheduled export", "Um usuario somente leitura, ou uma exportacao programada"),
               tx("La regla que indica que campo del asiento identifica la obra", "The rule saying which field on the entry identifies the job", "A regra que indica qual campo do lancamento identifica a obra")],
        note=tx("Es el mismo Bejerman, leido en vez de escrito. Separado del conector de arriba a proposito: cargar y leer son permisos distintos, y conviene que se vean distintos.",
                "The same Bejerman, read rather than written. Kept separate from the connector above on purpose: posting and reading are different permissions, and they should look different.",
                "O mesmo Bejerman, lido em vez de gravado. Separado do conector acima de proposito: lancar e ler sao permissoes diferentes, e convem que parecam diferentes."),
    ),
    dict(
        key="files", name=tx("Carpetas compartidas", "Shared folders", "Pastas compartilhadas"), category="files", status="connected", direction="in", every_minutes=15, phase="today",
        summary=tx("Lee las carpetas donde el equipo deja los archivos de obra: planillas de costos, mediciones, informes y comprobantes escaneados.",
                   "Reads the folders where the team leaves the job files: cost spreadsheets, measurements, reports and scanned documents.",
                   "Le as pastas onde a equipe deixa os arquivos de obra: planilhas de custos, medicoes, relatorios e documentos digitalizados."),
        reads=[tx("Planillas de control de costos (Excel)", "Cost control spreadsheets (Excel)", "Planilhas de controle de custos (Excel)"),
               tx("Informes y comprobantes (PDF, escaneos)", "Reports and documents (PDF, scans)", "Relatorios e documentos (PDF, digitalizacoes)"),
               tx("Mediciones y planillas de campo (CSV, Excel)", "Measurements and field sheets (CSV, Excel)", "Medicoes e planilhas de campo (CSV, Excel)")],
        method=tx("Revisa las carpetas cada 15 minutos. Lo nuevo o modificado pasa a Cargar datos, donde una persona revisa antes de guardar. Funciona igual sobre SharePoint, OneDrive, Google Drive o un servidor de archivos.",
                  "Checks the folders every 15 minutes. Anything new or changed goes to Load data, where a person reviews it before it is saved. Works the same over SharePoint, OneDrive, Google Drive or a file server.",
                  "Verifica as pastas a cada 15 minutos. O que e novo ou alterado vai para Carregar dados, onde uma pessoa revisa antes de salvar. Funciona igual sobre SharePoint, OneDrive, Google Drive ou um servidor de arquivos."),
        mapping=[(tx("Fila de costo de la planilla", "Cost row in the spreadsheet", "Linha de custo da planilha"), tx("Costo real por obra, actividad y mes", "Actual cost by job, activity and month", "Custo real por obra, atividade e mes")),
                 (tx("Comprobante escaneado", "Scanned document", "Documento digitalizado"), tx("Factura de proveedor, leida y verificada", "Supplier invoice, read and checked", "Fatura de fornecedor, lida e verificada"))],
        setup=[tx("Una cuenta de solo lectura sobre las carpetas", "A read-only account over the folders", "Uma conta somente leitura sobre as pastas"),
               tx("La lista de carpetas por obra o por zona", "The list of folders per job or zone", "A lista de pastas por obra ou zona")],
    ),
    dict(
        key="email", name=tx("Correo electronico", "Email", "E-mail"), category="email", status="connected", direction="in", every_minutes=15, phase="today",
        summary=tx("Toma los adjuntos que llegan por correo: facturas de proveedores, planillas y mediciones en CSV o Excel.",
                   "Takes the attachments that arrive by email: supplier invoices, spreadsheets and measurements in CSV or Excel.",
                   "Pega os anexos que chegam por e-mail: faturas de fornecedores, planilhas e medicoes em CSV ou Excel."),
        reads=[tx("Facturas de proveedores adjuntas (PDF, imagenes)", "Attached supplier invoices (PDF, images)", "Faturas de fornecedores anexadas (PDF, imagens)"),
               tx("Planillas y mediciones en CSV o Excel", "Spreadsheets and measurements in CSV or Excel", "Planilhas e medicoes em CSV ou Excel")],
        method=tx("Una casilla dedicada, por ejemplo facturas@, revisada cada 15 minutos. Se lee el adjunto, no el cuerpo del correo, y nada se registra sin que una persona lo apruebe.",
                  "A dedicated mailbox, for example invoices@, checked every 15 minutes. It reads the attachment, not the body of the message, and nothing is posted without a person approving it.",
                  "Uma caixa dedicada, por exemplo faturas@, verificada a cada 15 minutos. Le o anexo, nao o corpo da mensagem, e nada e lancado sem uma pessoa aprovar."),
        mapping=[(tx("Adjunto de factura", "Invoice attachment", "Anexo de fatura"), tx("Comprobante leido, verificado y a la espera de aprobacion", "Document read, checked and waiting for approval", "Documento lido, verificado e aguardando aprovacao")),
                 (tx("Planilla adjunta", "Attached spreadsheet", "Planilha anexada"), tx("Filas de costo o medicion, con su origen guardado", "Cost or measurement rows, with their source kept", "Linhas de custo ou medicao, com sua origem guardada"))],
        setup=[tx("Una casilla dedicada y permiso de solo lectura sobre ella", "A dedicated mailbox and read-only permission over it", "Uma caixa dedicada e permissao somente leitura sobre ela"),
               tx("Avisar a los proveedores que manden ahi", "Tell suppliers to send there", "Avisar os fornecedores para enviarem para la")],
        note=tx("Es por donde llega la mayor parte de las facturas. El cuerpo del correo no se usa para nada: lo que vale es el comprobante.",
                "This is where most invoices arrive. The body of the message is not used for anything: what counts is the document.",
                "E por onde chega a maior parte das faturas. O corpo da mensagem nao e usado: o que vale e o documento."),
    ),
    dict(
        key="provider_cloud", name=tx("Plataformas de proveedores externos", "External providers' platforms", "Plataformas de fornecedores externos"), category="files", status="available", direction="in", every_minutes=1440, phase="pilot",
        summary=tx("Baja la informacion que hoy queda en las plataformas en la nube de terceros, para que no haya que entrar a cada una por separado.",
                   "Pulls down the information that today sits in third parties' cloud platforms, so nobody has to log into each one separately.",
                   "Baixa a informacao que hoje fica nas plataformas em nuvem de terceiros, para nao ter que entrar em cada uma."),
        reads=[tx("Resultados de relevamientos e inspecciones", "Survey and inspection results", "Resultados de levantamentos e inspecoes"),
               tx("Registros de equipos y telemedicion", "Equipment and remote monitoring records", "Registros de equipamentos e telemedicao")],
        method=tx("Una lectura programada por plataforma, con las credenciales de ustedes y en modo de solo lectura. Si la plataforma no tiene forma de conectarse, se toma la exportacion que ya generan hoy.",
                  "A scheduled read per platform, with your own credentials and read-only. If a platform has no way to connect, it takes the export they already produce today.",
                  "Uma leitura programada por plataforma, com as credenciais de voces e somente leitura. Se a plataforma nao tiver como conectar, usa a exportacao que ja geram hoje."),
        mapping=[(tx("Registro de la plataforma", "Platform record", "Registro da plataforma"), tx("Medicion o evento, con fecha, ubicacion y origen", "Measurement or event, with date, location and source", "Medicao ou evento, com data, local e origem"))],
        setup=[tx("La lista de plataformas y quien las opera", "The list of platforms and who operates them", "A lista de plataformas e quem as opera"),
               tx("Un usuario de solo lectura en cada una", "A read-only user on each one", "Um usuario somente leitura em cada uma")],
        note=tx("Por definir en el diagnostico: cuales son y que permite cada una. Es la parte que mas depende de terceros y por eso figura como del piloto, no de hoy.",
                "To be settled in discovery: which ones they are and what each allows. This is the part that depends most on third parties, which is why it is marked for the pilot rather than today.",
                "A definir no diagnostico: quais sao e o que cada uma permite. E a parte que mais depende de terceiros, por isso figura como do piloto."),
    ),
    dict(
        key="geospatial", name=tx("Datos geoespaciales (SHP)", "Geospatial data (SHP)", "Dados geoespaciais (SHP)"), category="field", status="planned", direction="in", every_minutes=1440, phase="rollout",
        summary=tx("Leer la traza de las canerias y los puntos de medicion desde archivos SHP, para poder ubicar cada lectura sobre el terreno.",
                   "Read pipeline routes and measurement points from SHP files, so every reading can be placed on the ground.",
                   "Ler o tracado das tubulacoes e os pontos de medicao a partir de arquivos SHP, para localizar cada leitura no terreno."),
        reads=[tx("Traza de canerias y progresivas", "Pipeline routes and chainage", "Tracado de tubulacoes e estaqueamento"),
               tx("Ubicacion de postes de medicion, anodos y rectificadores", "Location of test posts, anodes and rectifiers", "Localizacao de postes de medicao, anodos e retificadores")],
        method=tx("Todavia no esta hecho. Es el siguiente paso de la consolidacion y figura asi a proposito: preferimos decirlo antes que mostrarlo resuelto en una pantalla.",
                  "Not built yet. It is the next step of the consolidation and is marked that way on purpose: we would rather say so than show it solved on a screen.",
                  "Ainda nao esta feito. E o proximo passo da consolidacao e figura assim de proposito: preferimos dizer antes de mostrar resolvido numa tela."),
        mapping=[(tx("Geometria de la traza", "Route geometry", "Geometria do tracado"), tx("Tramo de caneria, con su progresiva", "Pipeline section, with its chainage", "Trecho de tubulacao, com seu estaqueamento"))],
        setup=[tx("Los archivos SHP y el sistema de coordenadas que usan", "The SHP files and the coordinate system they use", "Os arquivos SHP e o sistema de coordenadas que usam")],
    ),
    dict(
        key="field_app", name=tx("Mediciones de campo", "Field measurements", "Medicoes de campo"), category="field", status="planned", direction="in", every_minutes=60, phase="rollout",
        summary=tx("Que las lecturas de campo lleguen el mismo dia: potenciales, relevamientos CIPS y DCVG, y la salida de los rectificadores.",
                   "Get the field readings in the same day: potentials, CIPS and DCVG surveys, and rectifier output.",
                   "Que as leituras de campo cheguem no mesmo dia: potenciais, levantamentos CIPS e DCVG, e a saida dos retificadores."),
        reads=[tx("Potenciales y criterios de proteccion", "Potentials and protection criteria", "Potenciais e criterios de protecao"),
               tx("Salida de rectificadores (tension y corriente)", "Rectifier output (voltage and current)", "Saida de retificadores (tensao e corrente)")],
        method=tx("Todavia no esta hecho. Depende de como se registren hoy las mediciones en obra, que es una de las cosas a mirar en el diagnostico.",
                  "Not built yet. It depends on how measurements are recorded on site today, which is one of the things to look at in discovery.",
                  "Ainda nao esta feito. Depende de como as medicoes sao registradas hoje em obra, que e uma das coisas a ver no diagnostico."),
        mapping=[(tx("Lectura de campo", "Field reading", "Leitura de campo"), tx("Medicion con fecha, punto y responsable", "Measurement with date, point and who took it", "Medicao com data, ponto e responsavel"))],
        setup=[tx("Como se registran hoy las mediciones", "How measurements are recorded today", "Como as medicoes sao registradas hoje")],
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


def _sync_bejerman(db: Session, when: datetime) -> dict:
    """Post every approved invoice, and leave the rest alone.

    The two numbers this returns are the whole pitch: how many went in
    without anybody typing, and how many are waiting for a person. The
    second is reported as a cost rather than hidden, because a connector
    that claims to have posted everything is a connector nobody checks.
    """
    from ..models import SupplierInvoice
    from . import invoices as inv

    approved = list(db.scalars(
        select(SupplierInvoice).where(SupplierInvoice.status == "approved")
    ))
    held = db.scalar(
        select(func.count()).select_from(SupplierInvoice)
        .where(SupplierInvoice.status == "held")
    ) or 0

    # Which route this installation uses. Until somebody confirms that
    # Bejerman exposes an import interface, the honest assumption is the
    # one that always works.
    route = "screen"
    posted = 0
    for invoice in approved:
        inv.post(db, invoice, route=route, now=when)
        posted += 1

    already = db.scalar(
        select(func.count()).select_from(SupplierInvoice)
        .where(SupplierInvoice.posted_reference.is_not(None))
    ) or 0
    minutes = sum(i.manual_minutes for i in approved)

    return dict(
        read=len(approved) + held, new=posted, updated=0, issues=held,
        status="attention" if held else "ok",
        details=dict(
            posted=posted, waiting_for_a_person=held, posted_to_date=already,
            route=route, minutes_not_typed=round(minutes),
        ),
    )


def _sync_email(db: Session, when: datetime) -> dict:
    """What came in as an attachment, and what it turned into.

    Most invoices arrive this way, so this is the connector somebody
    actually watches. It reports what was read and what is still waiting
    for a person, because a mailbox connector that only says "12 new
    messages" tells nobody anything useful.
    """
    from ..models import SupplierInvoice

    by_mail = list(db.scalars(
        select(SupplierInvoice).where(SupplierInvoice.channel.in_(("email", "portal")))
    ))
    waiting = [i for i in by_mail if i.status in ("read", "checked", "approved")]
    held = [i for i in by_mail if i.status == "held"]
    return dict(
        read=len(by_mail), new=0, updated=0, issues=len(held),
        status="attention" if held else "ok",
        details=dict(attachments=len(by_mail), waiting=len(waiting),
                     needs_a_person=len(held)),
    )


SYNC = {"files": _sync_files, "dynamics_gp": _sync_gp,
        "bejerman": _sync_bejerman, "email": _sync_email}


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
    elif key == "bejerman":
        from ..models import SupplierInvoice
        waiting = db.scalar(
            select(func.count()).select_from(SupplierInvoice)
            .where(SupplierInvoice.status == "approved")
        ) or 0
        detail = dict(route="screen", approved_and_waiting=waiting)
    else:
        from ..models import SupplierInvoice
        detail = dict(mailbox="facturas@montamar.example", attachments=db.scalar(
            select(func.count()).select_from(SupplierInvoice)
            .where(SupplierInvoice.channel.in_(("email", "portal")))
        ) or 0)
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
    if key == "email":
        from ..models import SupplierInvoice
        return db.scalar(
            select(func.count()).select_from(SupplierInvoice)
            .where(SupplierInvoice.channel.in_(("email", "portal")))
        ) or 0
    if key == "bejerman":
        from ..models import SupplierInvoice
        return db.scalar(select(func.count()).select_from(SupplierInvoice)) or 0
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
