"""Canonical project-control data model.

Every fact row (budget, cost, progress, change order, issue, schedule task) keeps
`document_id` + `locator` so any number in the UI can be traced back to the exact
cell, page or task of the source file it came from.
"""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Country(Base):
    __tablename__ = "countries"
    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    name_es: Mapped[str] = mapped_column(String(40))
    name_en: Mapped[str] = mapped_column(String(40))
    name_pt: Mapped[str] = mapped_column(String(40))
    currency: Mapped[str] = mapped_column(String(3))


class FxRate(Base):
    __tablename__ = "fx_rates"
    id: Mapped[int] = mapped_column(primary_key=True)
    currency: Mapped[str] = mapped_column(String(3), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)  # YYYY-MM
    usd_per_unit: Mapped[float] = mapped_column(Float)


class Activity(Base):
    __tablename__ = "activities"
    code: Mapped[str] = mapped_column(String(8), primary_key=True)
    kind: Mapped[str] = mapped_column(String(10))  # pipeline | civil | both
    sort: Mapped[int] = mapped_column(Integer)
    name_es: Mapped[str] = mapped_column(String(80))
    name_en: Mapped[str] = mapped_column(String(80))
    name_pt: Mapped[str] = mapped_column(String(80))


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    doc_type: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(200))
    filename: Mapped[str] = mapped_column(String(200))
    rel_path: Mapped[str] = mapped_column(String(300))  # relative to DATA_DIR
    language: Mapped[str] = mapped_column(String(2))
    pages: Mapped[int | None] = mapped_column(Integer)
    period: Mapped[str | None] = mapped_column(String(7))
    origin: Mapped[str] = mapped_column(String(10), default="seed")  # seed | upload
    checks: Mapped[dict | None] = mapped_column(JSON)  # parse-time validations (e.g. totals reconciled)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    page: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    country_code: Mapped[str] = mapped_column(ForeignKey("countries.code"))
    client: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(10))  # pipeline | civil
    status: Mapped[str] = mapped_column(String(10))  # active | closed
    contract_type: Mapped[str] = mapped_column(String(20))  # lump_sum | unit_price
    terrain: Mapped[str] = mapped_column(String(12))  # coast | highlands | rainforest
    region: Mapped[str] = mapped_column(String(60))
    diameter_in: Mapped[float | None] = mapped_column(Float)
    length_km: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3))
    contract_value: Mapped[float] = mapped_column(Float)
    bid_margin_pct: Mapped[float] = mapped_column(Float)  # fraction, e.g. 0.17
    start_period: Mapped[str] = mapped_column(String(7))
    planned_finish_period: Mapped[str] = mapped_column(String(7))
    forecast_finish_period: Mapped[str] = mapped_column(String(7))
    manager: Mapped[str] = mapped_column(String(60))
    description_es: Mapped[str] = mapped_column(Text, default="")
    description_en: Mapped[str] = mapped_column(Text, default="")
    description_pt: Mapped[str] = mapped_column(Text, default="")
    origin: Mapped[str] = mapped_column(String(10), default="seed")
    contract_document_id: Mapped[int | None] = mapped_column(Integer)
    contract_locator: Mapped[str | None] = mapped_column(String(60))
    bid_margin_document_id: Mapped[int | None] = mapped_column(Integer)
    bid_margin_locator: Mapped[str | None] = mapped_column(String(60))

    country: Mapped[Country] = relationship()


class BudgetLine(Base):
    __tablename__ = "budget_lines"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    activity_code: Mapped[str] = mapped_column(String(8))
    cost_type: Mapped[str] = mapped_column(String(4))  # MO | EQ | MAT | SUB | NA
    amount: Mapped[float] = mapped_column(Float)
    origin: Mapped[str] = mapped_column(String(15), default="original")  # original | change_order
    co_number: Mapped[str | None] = mapped_column(String(12))
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    locator: Mapped[str | None] = mapped_column(String(60))


class CostActual(Base):
    __tablename__ = "cost_actuals"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    activity_code: Mapped[str] = mapped_column(String(8))
    cost_type: Mapped[str] = mapped_column(String(4))
    amount: Mapped[float] = mapped_column(Float)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    locator: Mapped[str | None] = mapped_column(String(60))


class Progress(Base):
    __tablename__ = "progress"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    period: Mapped[str] = mapped_column(String(7))
    activity_code: Mapped[str] = mapped_column(String(8))
    planned_pct: Mapped[float] = mapped_column(Float)
    actual_pct: Mapped[float | None] = mapped_column(Float)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    locator: Mapped[str | None] = mapped_column(String(60))


class Production(Base):
    __tablename__ = "production"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    period: Mapped[str] = mapped_column(String(7))
    km_welded_cum: Mapped[float] = mapped_column(Float)
    welds_cum: Mapped[int] = mapped_column(Integer)
    weld_repairs_cum: Mapped[int] = mapped_column(Integer)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    locator: Mapped[str | None] = mapped_column(String(60))


class ChangeOrder(Base):
    __tablename__ = "change_orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    number: Mapped[str] = mapped_column(String(12))
    title_es: Mapped[str] = mapped_column(String(200))
    title_en: Mapped[str] = mapped_column(String(200))
    title_pt: Mapped[str] = mapped_column(String(200))
    cause: Mapped[str] = mapped_column(String(20))
    activity_code: Mapped[str] = mapped_column(String(8))
    amount: Mapped[float] = mapped_column(Float)  # revenue claimed, project currency
    status: Mapped[str] = mapped_column(String(10))  # approved | pending | rejected
    submitted_date: Mapped[str] = mapped_column(String(10))
    decision_date: Mapped[str | None] = mapped_column(String(10))
    schedule_impact_days: Mapped[int] = mapped_column(Integer, default=0)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    locator: Mapped[str | None] = mapped_column(String(60))


class Issue(Base):
    __tablename__ = "issues"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    period: Mapped[str] = mapped_column(String(7))
    category: Mapped[str] = mapped_column(String(20))
    activity_code: Mapped[str] = mapped_column(String(8))
    days_lost: Mapped[int] = mapped_column(Integer)
    cost_impact: Mapped[float] = mapped_column(Float)
    description_es: Mapped[str] = mapped_column(Text)
    description_en: Mapped[str] = mapped_column(Text)
    description_pt: Mapped[str] = mapped_column(Text)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    locator: Mapped[str | None] = mapped_column(String(60))


class ScheduleTask(Base):
    __tablename__ = "schedule_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    uid: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(120))
    activity_code: Mapped[str | None] = mapped_column(String(8))
    baseline_start: Mapped[str] = mapped_column(String(10))
    baseline_finish: Mapped[str] = mapped_column(String(10))
    start: Mapped[str] = mapped_column(String(10))
    finish: Mapped[str] = mapped_column(String(10))
    pct_complete: Mapped[float] = mapped_column(Float)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    locator: Mapped[str | None] = mapped_column(String(60))


class ProjectKpi(Base):
    """Materialized KPIs, refreshed after every seed or ingestion. Also queried by the Ask agent."""
    __tablename__ = "project_kpis"
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    as_of_period: Mapped[str] = mapped_column(String(7))
    progress_pct: Mapped[float] = mapped_column(Float)
    planned_pct: Mapped[float] = mapped_column(Float)
    bac: Mapped[float] = mapped_column(Float)
    ac: Mapped[float] = mapped_column(Float)
    ev: Mapped[float] = mapped_column(Float)
    pv: Mapped[float] = mapped_column(Float)
    eac: Mapped[float] = mapped_column(Float)
    cpi: Mapped[float | None] = mapped_column(Float)
    spi: Mapped[float | None] = mapped_column(Float)
    revised_contract: Mapped[float] = mapped_column(Float)
    approved_co_value: Mapped[float] = mapped_column(Float)
    pending_co_value: Mapped[float] = mapped_column(Float)
    pending_co_count: Mapped[int] = mapped_column(Integer)
    forecast_margin_value: Mapped[float] = mapped_column(Float)
    forecast_margin_pct: Mapped[float] = mapped_column(Float)
    bid_margin_pct: Mapped[float] = mapped_column(Float)
    margin_erosion_pts: Mapped[float] = mapped_column(Float)
    fx_usd: Mapped[float] = mapped_column(Float)
    contract_value_usd: Mapped[float] = mapped_column(Float)
    revised_contract_usd: Mapped[float] = mapped_column(Float)
    ac_usd: Mapped[float] = mapped_column(Float)
    eac_usd: Mapped[float] = mapped_column(Float)
    forecast_margin_usd: Mapped[float] = mapped_column(Float)
    pending_co_usd: Mapped[float] = mapped_column(Float)
    cost_overrun_pct: Mapped[float] = mapped_column(Float)  # EAC vs BAC
    weld_repair_rate: Mapped[float | None] = mapped_column(Float)
    days_lost_12m: Mapped[int] = mapped_column(Integer)
    delay_months: Mapped[int] = mapped_column(Integer)
    flags: Mapped[str] = mapped_column(String(200), default="")
    health: Mapped[str] = mapped_column(String(6))  # green | amber | red


class MappingTemplate(Base):
    __tablename__ = "mapping_templates"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    doc_kind: Mapped[str] = mapped_column(String(30))
    country_code: Mapped[str | None] = mapped_column(String(2))
    mapping: Mapped[dict] = mapped_column(JSON)
    times_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(200))
    stored_path: Mapped[str] = mapped_column(String(300))
    file_kind: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(12))  # preview | imported | failed
    ai_used: Mapped[bool] = mapped_column(Boolean, default=False)
    preview: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ErpTransaction(Base):
    """Rows of a Dynamics GP SmartList export (general ledger, project-segmented accounts)."""
    __tablename__ = "erp_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    trx_date: Mapped[str] = mapped_column(String(10))
    journal: Mapped[str] = mapped_column(String(20))
    account: Mapped[str] = mapped_column(String(30))
    cost_type: Mapped[str] = mapped_column(String(4))
    debit: Mapped[float] = mapped_column(Float)
    credit: Mapped[float] = mapped_column(Float)
    reference: Mapped[str] = mapped_column(String(60))
    source: Mapped[str] = mapped_column(String(20))
    vendor: Mapped[str | None] = mapped_column(String(60))
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    locator: Mapped[str | None] = mapped_column(String(60))


class Opportunity(Base):
    """A commercial opportunity (bid) read by the sales-system connector. Traced to the snapshot row it came from."""
    __tablename__ = "opportunities"
    id: Mapped[int] = mapped_column(primary_key=True)
    crm_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    client: Mapped[str] = mapped_column(String(80))
    country_code: Mapped[str] = mapped_column(ForeignKey("countries.code"))
    kind: Mapped[str] = mapped_column(String(10))  # pipeline | civil
    terrain: Mapped[str] = mapped_column(String(12))
    region: Mapped[str] = mapped_column(String(60))
    diameter_in: Mapped[float | None] = mapped_column(Float)
    length_km: Mapped[float | None] = mapped_column(Float)
    stage: Mapped[str] = mapped_column(String(20))  # prospecting | preparing | submitted | negotiation | won | lost
    currency: Mapped[str] = mapped_column(String(3))
    value: Mapped[float] = mapped_column(Float)
    bid_margin_pct: Mapped[float] = mapped_column(Float)
    probability: Mapped[float] = mapped_column(Float)
    expected_decision: Mapped[str] = mapped_column(String(7))  # YYYY-MM
    owner: Mapped[str] = mapped_column(String(60))
    next_step_es: Mapped[str] = mapped_column(Text, default="")
    next_step_en: Mapped[str] = mapped_column(Text, default="")
    next_step_pt: Mapped[str] = mapped_column(Text, default="")
    project_code: Mapped[str | None] = mapped_column(String(12))  # set when won
    lost_reason: Mapped[str | None] = mapped_column(String(20))  # price | postponed | scope
    modified_on: Mapped[str] = mapped_column(String(10))  # as reported by the sales system
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    locator: Mapped[str | None] = mapped_column(String(60))


class SyncRun(Base):
    """One execution of a connector: scheduled (simulated relative to now) or started by a person."""
    __tablename__ = "sync_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    connector: Mapped[str] = mapped_column(String(30), index=True)
    trigger: Mapped[str] = mapped_column(String(10))  # schedule | manual | test
    offset_minutes: Mapped[int | None] = mapped_column(Integer)  # seeded runs: minutes before "now"
    started_at: Mapped[datetime | None] = mapped_column(DateTime)  # runs started from the screen
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(10))  # ok | attention | error
    records_read: Mapped[int] = mapped_column(Integer, default=0)
    records_new: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    issues: Mapped[int] = mapped_column(Integer, default=0)
    details: Mapped[dict | None] = mapped_column(JSON)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))


class Meta(Base):
    __tablename__ = "meta"
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
