export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const isForm = typeof FormData !== "undefined" && init?.body instanceof FormData;
  let res: Response;
  try {
    res = await fetch(API_URL + path, {
      ...init,
      headers: { ...(init?.body && !isForm ? { "Content-Type": "application/json" } : {}), ...(init?.headers || {}) },
    });
  } catch {
    throw new ApiError("network");
  }
  if (res.status === 502 || res.status === 503 || res.status === 504) {
    throw new ApiError("network"); // server starting or waking up: callers retry
  }
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch {
      /* keep status text */
    }
    throw new ApiError(msg);
  }
  return res.json() as Promise<T>;
}

export const fileUrl = (path: string) => API_URL + path;

// ---------- shared types ----------
export type Lang = "es" | "en" | "pt";
export type Tri = Record<Lang, string>;
export type Health = "red" | "amber" | "green";

export interface ProjectRow {
  code: string;
  name: string;
  country: "EC" | "PE" | "BR";
  client: string;
  kind: "pipeline" | "civil";
  status: "active" | "closed";
  terrain: "coast" | "highlands" | "rainforest";
  region: string;
  currency: string;
  diameter_in: number | null;
  length_km: number | null;
  start_period: string;
  planned_finish: string;
  forecast_finish: string;
  progress_pct: number;
  planned_pct: number;
  cpi: number | null;
  spi: number | null;
  contract_value: number;
  contract_value_usd: number;
  revised_contract_usd: number;
  eac_usd: number;
  ac_usd: number;
  bid_margin_pct: number;
  forecast_margin_pct: number;
  margin_erosion_pts: number;
  forecast_margin_usd: number;
  pending_co_usd: number;
  pending_co_count: number;
  delay_months: number;
  days_lost_12m: number;
  weld_repair_rate: number | null;
  cost_overrun_pct: number;
  flags: string[];
  health: Health;
  origin: string;
  manager: string;
}

export interface Insight {
  code: "worst_project" | "pending_cos" | "terrain_erosion";
  severity: string;
  project?: string;
  params: Record<string, number | string | null>;
}

export interface Portfolio {
  status_period: string;
  summary: {
    active_count: number;
    closed_count: number;
    active_contract_usd: number;
    active_revised_usd: number;
    active_eac_usd: number;
    active_forecast_margin_pct: number | null;
    active_bid_margin_pct: number | null;
    pending_co_usd: number;
    pending_co_count: number;
    health: Record<Health, number>;
    days_lost_12m: number;
  };
  by_country: { country: string; projects: number; active: number; active_contract_usd: number; forecast_margin_pct: number | null; pending_co_usd: number }[];
  projects: ProjectRow[];
  insights: Insight[];
}

export interface SourceRef {
  document_id: number | null;
  locator: string | null;
}

export interface ActivityRow {
  code: string;
  names: Tri;
  bac: number;
  budget_orig: number;
  budget_co: number;
  ac: number;
  ev: number;
  pv: number;
  eac: number;
  pct: number;
  planned: number;
  cpi: number | null;
  variance: number;
}

export interface ChangeOrderRow extends SourceRef {
  id: number;
  number: string;
  titles: Tri;
  cause: string;
  activity: string;
  amount: number;
  amount_usd: number;
  status: "approved" | "pending" | "rejected";
  submitted_date: string;
  decision_date: string | null;
  days_pending: number | null;
  schedule_impact_days: number;
}

export interface IssueRow extends SourceRef {
  id: number;
  period: string;
  category: string;
  activity: string;
  days_lost: number;
  cost_impact: number;
  descriptions: Tri;
}

export interface TaskRow extends SourceRef {
  uid: number;
  name: string;
  activity: string | null;
  baseline_start: string;
  baseline_finish: string;
  start: string;
  finish: string;
  pct: number;
}

export interface DocRow {
  id: number;
  doc_type: string;
  title: string;
  filename: string;
  language: string;
  pages: number | null;
  period: string | null;
  origin: string;
}

export interface ProjectDetail {
  project: ProjectRow & {
    descriptions: Tri;
    contract_type: string;
    fx_usd: number;
    as_of_period: string;
    contract_source: SourceRef;
    bid_margin_source: SourceRef;
  };
  kpis: {
    progress_pct: number;
    planned_pct: number;
    bac: number;
    ac: number;
    ev: number;
    pv: number;
    eac: number;
    cpi: number | null;
    spi: number | null;
    revised_contract: number;
    approved_co_value: number;
    pending_co_value: number;
    pending_co_count: number;
    forecast_margin_value: number;
    forecast_margin_pct: number;
    bid_margin_pct: number;
    margin_erosion_pts: number;
    fx_usd: number;
    cost_overrun_pct: number;
    weld_repair_rate: number | null;
    days_lost_12m: number;
    delay_months: number;
    flags: string[];
    health: Health;
    oldest_pending_days: number;
  };
  activities: ActivityRow[];
  waterfall: { steps: { key: string; code?: string; value: number }[]; revised_contract: number; pending_recovery: number };
  scurve: { period: string; pv: number | null; ev: number | null; ac: number | null; month_cost: number }[];
  change_orders: ChangeOrderRow[];
  issues: IssueRow[];
  schedule: TaskRow[];
  production: (SourceRef & { period: string; km: number; welds: number; repairs: number; repair_rate: number | null })[];
  documents: DocRow[];
  drivers: { activity: string; variance: number; share: number; cos: string[]; issues: number[]; standby_cost: number; days_lost: number }[];
  anomalies: Anomaly[];
  erp: Recon;
}

export type AnomalyExplanation =
  | { kind: "issue"; category: string; days_lost: number; descriptions: Tri; document_id: number | null; locator: string | null }
  | { kind: "change_order"; number: string; status: string; titles: Tri; document_id: number | null; locator: string | null };

export interface Anomaly extends SourceRef {
  period: string;
  activity: string;
  cost: number;
  expected: number;
  excess: number;
  progress_gain: number;
  explanation: AnomalyExplanation | null;
  project?: string;
  project_name?: string;
  currency?: string;
  excess_usd?: number;
}

export interface Discrepancy {
  project: string;
  project_name: string;
  currency: string;
  period: string;
  cost_type: string;
  kind: "missing_in_excel" | "missing_in_erp" | "duplicate";
  erp_amount: number;
  excel_amount: number;
  diff: number;
  diff_usd: number;
  erp_rows: (SourceRef & { reference: string; vendor: string | null; trx_date: string; account: string; amount: number })[];
  excel_cells: (SourceRef & { activity: string; amount: number })[];
}

export interface Recon {
  cells: number;
  matched: number;
  match_rate: number | null;
  erp_total_usd: number;
  erp_transactions?: number;
  projects: number;
  discrepancies: Discrepancy[];
}

export interface ModelMetrics {
  name: string;
  algorithm: string;
  n_train: number;
  n_test: number;
  classes: number;
  accuracy: number;
  errors: Record<string, string>[];
}

export interface Check {
  code: string;
  ok: boolean;
  params?: Record<string, unknown>;
}

export interface WorkbookCheck {
  document_id: number;
  title: string;
  filename: string;
  project: string | null;
  ok: boolean;
  checks: Check[];
}

export interface ReportCheck {
  project: string;
  project_name: string;
  currency: string;
  period: string;
  reported: number;
  workbook: number;
  diff: number;
  ok: boolean;
  document_id: number;
  locator: string;
  workbook_document_id: number | null;
}

export interface Datahub {
  files: { total: number; by_type: Record<string, number>; by_ext: Record<string, number>; by_language: Record<string, number>; uploaded: number };
  records: Record<string, number>;
  records_total: number;
  projects: number;
  countries: number;
  coverage: { project: string; name: string; country: string; status: string; origin: string; docs: Record<string, number>; erp: boolean }[];
  templates: { name: string; country: string | null; times_used: number }[];
  quality: {
    lineage: { total: number; traced: number; rate: number };
    workbook_totals: { checked: number; passed: number; failed: { document_id: number; title: string }[]; items: WorkbookCheck[] };
    report_vs_workbook: { checked: number; matched: number; mismatches: ReportCheck[]; items: ReportCheck[] };
    erp_vs_excel: Recon;
  };
  anomalies: { count: number; unexplained: number; items: Anomaly[] };
  models: Record<string, ModelMetrics>;
  ingestion: Record<string, number>;
  ai_enabled: boolean;
}

export interface Meta {
  status_period: string;
  countries: Record<string, { names: Tri; currency: string }>;
  activities: Record<string, Tri>;
  cost_types: Record<string, Tri>;
  terrains: Record<string, Tri>;
  issue_categories: Record<string, Tri>;
  co_causes: Record<string, Tri>;
  co_status: Record<string, Tri>;
  flags: Record<string, string>;
}

export interface Health_ {
  status: string;
  ai_enabled: boolean;
  model: string | null;
  status_period: string;
  projects: number;
  documents: number;
}

// ---------- connectors and bids ----------
export type ConnectorStatus = "connected" | "available" | "planned";

export interface SyncRun {
  id: number;
  trigger: "schedule" | "manual";
  at: string;
  duration_ms: number;
  status: "ok" | "attention" | "error";
  read: number;
  new: number;
  updated: number;
  issues: number;
  details: {
    waiting?: string[];
    folders?: number;
    exports?: number;
    matched?: number;
    cells?: number;
    differences?: number;
    changes?: { crm_id: string; name: string; kind: "new" | "updated"; currency?: string; fields?: { field: string; old: unknown; new: unknown }[] }[];
  };
  document_id: number | null;
}

export interface Connector {
  key: string;
  name: Tri;
  category: "files" | "accounting" | "sales" | "schedules" | "email" | "reporting" | "field";
  status: ConnectorStatus;
  direction: "in" | "out";
  every_minutes: number;
  phase: "today" | "pilot" | "after_decision" | "rollout";
  summary: Tri;
  reads: Tri[];
  method: Tri;
  mapping: { source: Tri; target: Tri }[];
  setup: Tri[];
  note?: Tri;
  records: number;
  last_run?: SyncRun | null;
  next_in_minutes?: number;
  runs?: SyncRun[];
}

export interface ConnectorsResp {
  now: string;
  connectors: Connector[];
  summary: { connected: number; available: number; planned: number; records: number; attention: number; waiting_files: number };
}

export interface BidCheck {
  risk: "red" | "amber" | "green" | "none";
  reason?: string;
  affordable_cost_usd?: number;
  history_cost_usd?: number;
  history_low_usd?: number;
  history_high_usd?: number;
  gap?: number;
  margin_left?: number;
  typical_erosion?: number;
  contingency?: number;
  price_needed_usd?: number;
  price_gap_usd?: number;
  sample?: string[];
}

export interface Bid extends SourceRef {
  crm_id: string;
  name: string;
  client: string;
  country: "EC" | "PE" | "BR";
  kind: "pipeline" | "civil";
  terrain: "coast" | "highlands" | "rainforest";
  region: string;
  diameter_in: number | null;
  length_km: number | null;
  stage: "prospecting" | "preparing" | "submitted" | "negotiation" | "won" | "lost";
  currency: string;
  value: number;
  value_usd: number;
  bid_margin_pct: number;
  probability: number;
  weighted_usd: number;
  expected_decision: string;
  owner: string;
  next_step: Tri;
  project_code: string | null;
  lost_reason: string | null;
  modified_on: string;
  check?: BidCheck;
  comparables?: { code: string; name: string; country: string; diameter_in: number; length_km: number; cost_per_km_usd: number; margin_delta_pts: number; overrun_pct: number | null }[];
}

export interface BidsResp {
  bids: Bid[];
  summary: {
    open_count: number;
    open_value_usd: number;
    weighted_usd: number;
    red_count: number;
    red_value_usd: number;
    amber_count: number;
    amber_value_usd: number;
    won_count: number;
    won_value_usd: number;
    lost_count: number;
    win_rate: number | null;
  };
  last_sync: SyncRun | null;
}
