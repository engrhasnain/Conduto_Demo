from ...config import STATUS_PERIOD

VIEW_SQL = """
CREATE VIEW IF NOT EXISTS v_project_overview AS
SELECT p.code, p.name, p.country_code, p.client, p.kind, p.status, p.terrain, p.region, p.diameter_in, p.length_km,
       p.currency, p.contract_value, p.start_period, p.planned_finish_period, p.forecast_finish_period, p.manager,
       k.as_of_period, k.progress_pct, k.planned_pct, k.cpi, k.spi, k.bac, k.ac, k.ev, k.pv, k.eac,
       k.revised_contract, k.approved_co_value, k.pending_co_value, k.pending_co_count, k.forecast_margin_value,
       k.forecast_margin_pct, k.bid_margin_pct, k.margin_erosion_pts, k.cost_overrun_pct, k.fx_usd,
       k.contract_value_usd, k.revised_contract_usd, k.ac_usd, k.eac_usd, k.forecast_margin_usd, k.pending_co_usd,
       k.weld_repair_rate, k.days_lost_12m, k.delay_months, k.flags, k.health, p.id AS project_id
FROM projects p JOIN project_kpis k ON k.project_id = p.id
"""

SCHEMA_DOC = f"""SQLite database of Conduto's consolidated project controls. Data cut-off (status) period: {STATUS_PERIOD}.
Money is in each project's own currency (projects.currency: USD, PEN, BRL) unless the column ends in _usd
(converted at the {STATUS_PERIOD} reporting rate; project_kpis.fx_usd = USD per unit of local currency).
Ratios are fractions (0.17 = 17%). Periods are text 'YYYY-MM'; dates 'YYYY-MM-DD'.

VIEW v_project_overview — one row per project; start here for portfolio questions. Columns:
  code, name, country_code (EC Ecuador | PE Peru | BR Brazil), client, kind (pipeline|civil), status (active|closed),
  terrain (coast|highlands|rainforest), region, diameter_in, length_km, currency, contract_value, start_period,
  planned_finish_period, forecast_finish_period, manager, as_of_period, progress_pct, planned_pct,
  cpi, spi (NULL when closed), bac (budget incl. approved change orders), ac (actual cost to date), ev, pv,
  eac (estimate at completion; final cost when closed), revised_contract (contract + approved COs),
  approved_co_value, pending_co_value, pending_co_count, forecast_margin_value, forecast_margin_pct (final margin when closed),
  bid_margin_pct, margin_erosion_pts (bid minus forecast, a fraction: 0.125 = 12.5 points), cost_overrun_pct (eac/bac - 1),
  fx_usd, contract_value_usd, revised_contract_usd, ac_usd, eac_usd, forecast_margin_usd, pending_co_usd,
  weld_repair_rate, days_lost_12m, delay_months, flags (comma list of COST_OVERRUN, SCHEDULE_DELAY, MARGIN_EROSION,
  PENDING_CO, PENDING_CO_AGING, WELD_QUALITY), health (green|amber|red), project_id

TABLE activities(code, kind, name_es, name_en, name_pt) — canonical cost breakdown.
  Pipeline: MOV mobilization & camps, DDV right-of-way clearing, ZAN trenching, TEN stringing & bending, SOL welding,
  END non-destructive testing, REV field joint coating, BAJ lowering-in & backfill, CRU special crossings (HDD),
  PH hydrostatic testing, RES environmental restoration, IND indirects & supervision.
  Civil: MOV, EXC earthworks, CIM foundations & concrete, EST steel structures, MEC mechanical installation,
  ELE electrical & instrumentation, PRU testing & commissioning, IND.
TABLE budget_lines(project_id, activity_code, cost_type, amount, origin, co_number)
  cost_type: MO labor | EQ equipment | MAT materials | SUB subcontracts | NA not itemized; origin: original | change_order
TABLE cost_actuals(project_id, period, activity_code, cost_type, amount) — monthly actual cost
TABLE progress(project_id, period, activity_code, planned_pct, actual_pct) — cumulative physical progress
TABLE production(project_id, period, km_welded_cum, welds_cum, weld_repairs_cum) — pipelines, cumulative
TABLE change_orders(project_id, number, title_es, title_en, title_pt, cause, activity_code, amount, status,
  submitted_date, decision_date, schedule_impact_days)
  status: approved | pending | rejected; cause: client_request | design | geotech | community | permits | scope | weather | escalation
TABLE issues(project_id, period, category, activity_code, days_lost, cost_impact, description_es, description_en, description_pt)
  category: weather | community | permits | geotech | quality | supply | equipment | force_majeure
TABLE schedule_tasks(project_id, uid, name, activity_code, baseline_start, baseline_finish, start, finish, pct_complete)
TABLE erp_transactions(project_id, period, trx_date, journal, account, cost_type, debit, credit, reference, source, vendor)
  Dynamics GP general-ledger lines (12-month export, active projects). GP books by cost_type, not by activity;
  compare with SUM(cost_actuals.amount) by project, period and cost_type to reconcile ERP vs Excel.
TABLE fx_rates(currency, period, usd_per_unit)
TABLE documents(id, project_id, doc_type, title, filename, period)
  doc_type: cost_workbook | schedule | contract | change_order | progress_report | closeout_report | legacy_workbook
Join facts to projects with project_id = v_project_overview.project_id (or projects.id).
"""
