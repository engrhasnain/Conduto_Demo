"use client";

import clsx from "clsx";
import { AlertTriangle, ArrowRight, Brain, CheckCircle2, ChevronRight, Download, FileSpreadsheet, FileText, GanttChart, Landmark, Layers, ShieldCheck, XCircle } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useApp } from "@/components/providers";
import { Badge, Card, DetailDrawer, ErrorState, Loading, PageHeader, Select, SourceLink, Td, Th } from "@/components/ui";
import { API_URL, type Anomaly, type Check, type Datahub, type Discrepancy, type DocRow } from "@/lib/api";
import { money, num, pct, period } from "@/lib/format";
import { useApi } from "@/lib/useApi";

function useCountUp(target: number, ms = 1100) {
  const [v, setV] = useState(0);
  useEffect(() => {
    let raf = 0;
    const t0 = performance.now();
    const tick = (now: number) => {
      const k = Math.min((now - t0) / ms, 1);
      setV(target * (1 - Math.pow(1 - k, 3)));
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, ms]);
  return v;
}

function Counter({ value, label, suffix = "", digits = 0, onClick }: { value: number; label: string; suffix?: string; digits?: number; onClick: () => void }) {
  const { lang } = useApp();
  const v = useCountUp(value);
  return (
    <button onClick={onClick} className="group min-w-0 rounded-lg p-1 -m-1 text-left hover:bg-white/5">
      <p className="text-[34px] font-semibold leading-none tracking-tight text-white">{num(v, lang, digits)}{suffix}</p>
      <p className="mt-2 flex items-center gap-1 text-[12.5px] text-sky-200/80 group-hover:text-white">{label} <ChevronRight className="h-3 w-3 opacity-60" /></p>
    </button>
  );
}

function Ring({ value, ok }: { value: number; ok: boolean }) {
  const r = 26, c = 2 * Math.PI * r;
  return (
    <svg width="66" height="66" viewBox="0 0 66 66" className="shrink-0" aria-hidden>
      <circle cx="33" cy="33" r={r} fill="none" stroke="#eef0f3" strokeWidth="7" />
      <circle cx="33" cy="33" r={r} fill="none" stroke={ok ? "#0ca30c" : "#fab219"} strokeWidth="7" strokeLinecap="round"
        strokeDasharray={`${c * Math.min(value, 1)} ${c}`} transform="rotate(-90 33 33)" />
    </svg>
  );
}

function QualityCard({ title, value, sub, ratio, ok, onClick }: { title: string; value: string; sub: string; ratio: number; ok: boolean; onClick: () => void }) {
  const { t } = useApp();
  return (
    <button onClick={onClick} className="group flex items-center gap-4 rounded-xl bg-white p-4 text-left ring-1 ring-black/[0.07] transition-shadow hover:shadow-md hover:ring-[#2a78d6]/40">
      <Ring value={ratio} ok={ok} />
      <div className="min-w-0">
        <p className="flex items-center gap-1.5 text-[12.5px] font-medium text-slate-500">
          {ok ? <CheckCircle2 className="h-3.5 w-3.5 text-[#0ca30c]" /> : <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />} {title}
        </p>
        <p className="text-[24px] font-semibold tracking-tight text-slate-900">{value}</p>
        <p className="text-[12px] leading-snug text-slate-500">{sub}</p>
        <p className="mt-1 flex items-center gap-0.5 text-[11.5px] font-medium text-[#2a78d6] opacity-70 group-hover:opacity-100">{t("common.details")} <ChevronRight className="h-3 w-3" /></p>
      </div>
    </button>
  );
}

function ErpFinding({ d }: { d: Discrepancy }) {
  const { t, lang, label } = useApp();
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3">
      <Badge tone={d.kind === "duplicate" ? "red" : "violet"}><Landmark className="h-3 w-3" /> {t("dh.erp_col")}</Badge>
      <div className="min-w-[240px] flex-1">
        <p className="text-[13.5px] font-medium text-slate-900">{t(`dh.f.${d.kind}`)}</p>
        <p className="text-[12.5px] text-slate-500">
          <Link href={`/projects/${d.project}`} className="font-semibold text-[#2a78d6] hover:underline">{d.project}</Link> · {period(d.period, lang)} · {label("cost_types", d.cost_type)} ·{" "}
          {t("dh.f.erp_detail", { erp: money(d.erp_amount, lang, d.currency), excel: money(d.excel_amount, lang, d.currency) })}
          {d.erp_rows[0] && d.kind !== "missing_in_erp" ? ` · ${d.erp_rows[0].reference}${d.erp_rows[0].vendor ? ` (${d.erp_rows[0].vendor})` : ""}` : ""}
        </p>
      </div>
      <p className={clsx("w-28 text-right text-[14px] font-semibold tabular-nums", d.diff > 0 ? "text-red-700" : "text-amber-700")}>{d.diff > 0 ? "+" : ""}{money(d.diff_usd, lang)}</p>
      <div className="flex w-56 flex-wrap justify-end gap-3">
        {d.erp_rows[0] && <SourceLink document_id={d.erp_rows[0].document_id} locator={d.erp_rows[0].locator}>{t("dh.src.erp")}</SourceLink>}
        {d.excel_cells[0] && <SourceLink document_id={d.excel_cells[0].document_id} locator={d.excel_cells[0].locator}>{t("dh.src.excel")}</SourceLink>}
      </div>
    </div>
  );
}

function AnomalyRow({ a, max }: { a: Anomaly; max: number }) {
  const { t, lang, label } = useApp();
  return (
    <div className="grid grid-cols-[88px_minmax(0,1fr)_120px] items-center gap-3 px-5 py-2.5 text-[13px]">
      <Link href={`/projects/${a.project}`} className="font-semibold text-[#2a78d6] hover:underline">{a.project}</Link>
      <div className="min-w-0">
        <p className="truncate text-slate-800">{period(a.period, lang)} · {label("activities", a.activity)}</p>
        <div className="mt-1 flex items-center gap-2">
          <div className="h-1.5 flex-1 rounded-full bg-slate-100">
            <div className={clsx("h-1.5 rounded-full", a.explanation ? "bg-[#6da7ec]" : "bg-[#d03b3b]")} style={{ width: `${((a.excess_usd ?? 0) / max) * 100}%` }} />
          </div>
          {a.explanation ? (
            <SourceLink document_id={a.explanation.document_id} locator={a.explanation.locator} className="shrink-0">
              {t("dh.explained_by")}: {a.explanation.kind === "issue" ? label("issue_categories", a.explanation.category) : a.explanation.number}
            </SourceLink>
          ) : <Badge tone="red">{t("dh.unexplained")}</Badge>}
          <SourceLink document_id={a.document_id} locator={a.locator} className="shrink-0">{t("dh.src.excel")}</SourceLink>
        </div>
      </div>
      <p className="text-right font-medium tabular-nums text-slate-900">+{money(a.excess_usd ?? 0, lang)}</p>
    </div>
  );
}

function CheckList({ checks }: { checks: Check[] }) {
  const { t, lang } = useApp();
  const fmt = (v: unknown) => (typeof v === "number" ? num(v, lang, Number.isInteger(v) ? 0 : 2) : Array.isArray(v) ? v.join(", ") : String(v ?? ""));
  return (
    <ul className="space-y-1">
      {checks.map((c, i) => (
        <li key={i} className="flex items-start gap-1.5 text-[12.5px]">
          {c.ok ? <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#0ca30c]" /> : <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#d03b3b]" />}
          <span className={c.ok ? "text-slate-600" : "font-medium text-red-800"}>
            {t(`chk.${c.code}.${c.ok ? "ok" : "fail"}`, Object.fromEntries(Object.entries(c.params ?? {}).map(([k, v]) => [k, fmt(v)])))}
          </span>
        </li>
      ))}
    </ul>
  );
}

/** Documents behind a number: fetched on demand, each opens in the source viewer. */
function DocList({ query }: { query: string }) {
  const { t, lang, openSource } = useApp();
  const { data, error } = useApi<(DocRow & { project: string | null })[]>(`/api/documents?${query}`);
  if (error) return <ErrorState message={error} />;
  if (!data) return <Loading />;
  if (!data.length) return <p className="text-sm text-slate-400">{t("pj.none")}</p>;
  return (
    <table className="min-w-full text-[13px]">
      <thead className="border-b border-slate-200"><tr><Th>{t("pf.col.project")}</Th><Th>{t("pj.col.doc")}</Th><Th>{t("pj.col.month")}</Th></tr></thead>
      <tbody className="divide-y divide-slate-100">
        {data.map((d) => {
          const Icon = d.doc_type.includes("workbook") || d.doc_type === "erp_export" ? FileSpreadsheet : d.doc_type === "schedule" ? GanttChart : FileText;
          return (
            <tr key={d.id} className="cursor-pointer hover:bg-blue-50/40" onClick={() => openSource({ kind: "source", document_id: d.id, locator: d.pages ? "p.1" : null })}>
              <Td className="whitespace-nowrap font-semibold text-slate-800">{d.project ?? "—"}</Td>
              <Td>
                <span className="flex items-center gap-2">
                  <Icon className="h-4 w-4 shrink-0 text-[#1f3a5f]" />
                  <span className="min-w-0">
                    <span className="block text-slate-800">{d.title}</span>
                    <span className="block text-[11.5px] text-slate-400">{t(`doc.${d.doc_type}`)} · {d.filename}</span>
                  </span>
                </span>
              </Td>
              <Td className="whitespace-nowrap text-slate-500">{d.period ? period(d.period, lang) : "—"}</Td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

const DOC_COLS: [string, typeof FileText][] = [
  ["cost_workbook", FileSpreadsheet], ["schedule", GanttChart], ["contract", FileText], ["change_order", FileText],
  ["progress_report", FileText], ["closeout_report", FileText], ["legacy_workbook", FileSpreadsheet],
];
const RECORD_KINDS = ["cost_actuals", "budget_lines", "progress", "production", "change_orders", "issues", "schedule_tasks", "erp_transactions", "document_pages"];

type Panel =
  | null
  | { kind: "docs"; title: string; query: string }
  | { kind: "records" | "lineage" | "workbooks" | "reports" | "erp" };

export default function DataPage() {
  const { t, lang, country, label } = useApp();
  const { data, error, loading, reload } = useApi<Datahub>("/api/datahub");
  const [ctry, setCtry] = useState<"all" | "EC" | "PE" | "BR">("all");
  const [panel, setPanel] = useState<Panel>(null);

  const inCountry = useMemo(() => {
    const m = new Map((data?.coverage ?? []).map((c) => [c.project, c.country]));
    return (code?: string | null) => ctry === "all" || (!!code && m.get(code) === ctry);
  }, [data, ctry]);

  if (error && !data) return <ErrorState message={error} onRetry={reload} />;
  if (loading || !data) return <Loading />;
  const q = data.quality;
  const erp = q.erp_vs_excel;
  const rep = q.report_vs_workbook;
  const repItems = rep.items ?? rep.mismatches;
  const wbItems = q.workbook_totals.items ?? [];
  const discrepancies = erp.discrepancies.filter((d) => inCountry(d.project));
  const mismatches = rep.mismatches.filter((m) => inCountry(m.project));
  const anomalies = data.anomalies.items.filter((a) => inCountry(a.project));
  const unexplained = anomalies.filter((a) => !a.explanation);
  const coverage = data.coverage.filter((c) => inCountry(c.project));
  const findingsCount = discrepancies.length + mismatches.length + unexplained.length;
  const bt = data.files.by_type;
  const excel = (bt.cost_workbook ?? 0) + (bt.legacy_workbook ?? 0);
  const pdfs = (bt.contract ?? 0) + (bt.change_order ?? 0) + (bt.progress_report ?? 0) + (bt.closeout_report ?? 0);
  const maxExcess = Math.max(...anomalies.map((a) => a.excess_usd ?? 0), 1);
  const docs = (title: string, query: string) => setPanel({ kind: "docs", title, query });
  const chip = "inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 hover:bg-white/20";

  return (
    <div className="space-y-6">
      <PageHeader title={t("dh.title")} subtitle={t("dh.sub")}>
        <div className="flex items-center gap-2">
          <Select label={t("pf.f.country")} value={ctry} onChange={setCtry} options={[
            { value: "all", label: t("common.all") }, { value: "EC", label: country("EC") }, { value: "PE", label: country("PE") }, { value: "BR", label: country("BR") }]} />
        </div>
      </PageHeader>

      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#0f2440] via-[#132a45] to-[#1c5cab] p-6 text-white shadow-lg lg:p-8">
        <div className="pointer-events-none absolute -right-20 -top-24 h-72 w-72 rounded-full bg-sky-400/10 blur-2xl" />
        <p className="text-[12px] font-semibold uppercase tracking-[0.18em] text-sky-300">{t("dh.hero")}</p>
        <div className="mt-5 grid grid-cols-2 items-center gap-6 lg:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr]">
          <Counter value={data.files.total} label={t("dh.files")} onClick={() => docs(t("dh.files"), "")} />
          <ArrowRight className="hidden h-5 w-5 text-sky-300/70 lg:block" />
          <Counter value={data.records_total} label={t("dh.records")} onClick={() => setPanel({ kind: "records" })} />
          <ArrowRight className="hidden h-5 w-5 text-sky-300/70 lg:block" />
          <Link href="/" className="group -m-1 rounded-lg p-1 hover:bg-white/5">
            <p className="text-[34px] font-semibold leading-none tracking-tight">{data.projects}<span className="text-sky-300/80"> · </span>{data.countries}</p>
            <p className="mt-2 flex items-center gap-1 text-[12.5px] text-sky-200/80 group-hover:text-white">{t("dh.projects")} <ChevronRight className="h-3 w-3 opacity-60" /></p>
          </Link>
          <ArrowRight className="hidden h-5 w-5 text-sky-300/70 lg:block" />
          <Counter value={q.lineage.rate * 100} suffix="%" label={t("dh.traceable")} onClick={() => setPanel({ kind: "lineage" })} />
        </div>
        <div className="mt-6 flex flex-wrap items-center gap-2 text-[12.5px]">
          <button className={chip} onClick={() => docs(t("dh.chip.excel"), "doc_type=cost_workbook,legacy_workbook")}><FileSpreadsheet className="h-3.5 w-3.5" /> Excel · {excel}</button>
          <button className={chip} onClick={() => docs(t("doc.schedule"), "doc_type=schedule")}><GanttChart className="h-3.5 w-3.5" /> Microsoft Project · {bt.schedule ?? 0}</button>
          <button className={chip} onClick={() => docs(t("dh.chip.pdf"), "doc_type=contract,change_order,progress_report,closeout_report")}><FileText className="h-3.5 w-3.5" /> PDF · {pdfs}</button>
          <button className={chip} onClick={() => docs(t("doc.erp_export"), "doc_type=erp_export")}><Landmark className="h-3.5 w-3.5" /> Dynamics GP · {bt.erp_export ?? 0}</button>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1"><Layers className="h-3.5 w-3.5" /> {t("dh.langs")}</span>
          <a href={`${API_URL}/api/export/consolidated.xlsx?lang=${lang}`} className="ml-auto inline-flex items-center gap-2 rounded-lg bg-white px-3.5 py-2 text-[13px] font-semibold text-[#132a45] hover:bg-sky-50" title={t("dh.export_hint")}>
            <Download className="h-4 w-4" /> {t("dh.export")}
          </a>
        </div>
        <p className="mt-3 text-[12px] text-sky-200/70">{t("dh.hero_hint")}</p>
      </section>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <QualityCard title={t("dh.q.lineage")} value={pct(q.lineage.rate, lang, 0)} ratio={q.lineage.rate} ok={q.lineage.rate >= 0.999} onClick={() => setPanel({ kind: "lineage" })}
          sub={t("dh.q.lineage_sub", { traced: num(q.lineage.traced, lang), total: num(q.lineage.total, lang) })} />
        <QualityCard title={t("dh.q.workbooks")} value={`${q.workbook_totals.passed}/${q.workbook_totals.checked}`} ratio={q.workbook_totals.passed / Math.max(q.workbook_totals.checked, 1)} onClick={() => setPanel({ kind: "workbooks" })}
          ok={q.workbook_totals.passed === q.workbook_totals.checked} sub={t("dh.q.workbooks_sub", { passed: q.workbook_totals.passed, checked: q.workbook_totals.checked })} />
        <QualityCard title={t("dh.q.reports")} value={`${rep.matched}/${rep.checked}`} ratio={rep.matched / Math.max(rep.checked, 1)} onClick={() => setPanel({ kind: "reports" })}
          ok={rep.mismatches.length === 0} sub={t("dh.q.reports_sub", { matched: rep.matched, checked: rep.checked })} />
        <QualityCard title={t("dh.q.erp")} value={pct(erp.match_rate, lang, 1)} ratio={erp.match_rate ?? 0} ok={erp.discrepancies.length === 0} onClick={() => setPanel({ kind: "erp" })}
          sub={t("dh.q.erp_sub", { n: num(erp.erp_transactions ?? 0, lang), d: erp.discrepancies.length })} />
      </div>

      <Card title={<span className="flex items-center gap-2"><AlertTriangle className="h-4 w-4 text-amber-600" /> {t("dh.findings")} <Badge tone="amber">{findingsCount}</Badge></span>}
        subtitle={t("dh.findings_sub")} bodyClass="px-0 pb-2">
        <div className="divide-y divide-slate-100">
          {discrepancies.map((d, i) => <ErpFinding key={`erp${i}`} d={d} />)}
          {mismatches.map((m, i) => (
            <div key={`rep${i}`} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3">
              <Badge tone="amber"><FileText className="h-3 w-3" /> PDF</Badge>
              <div className="min-w-[240px] flex-1">
                <p className="text-[13.5px] font-medium text-slate-900">{t("dh.f.stale_report")}</p>
                <p className="text-[12.5px] text-slate-500">
                  <Link href={`/projects/${m.project}`} className="font-semibold text-[#2a78d6] hover:underline">{m.project}</Link> · {period(m.period, lang)} ·{" "}
                  {t("dh.f.report_detail", { reported: money(m.reported, lang, m.currency), workbook: money(m.workbook, lang, m.currency) })}
                </p>
              </div>
              <p className="w-28 text-right text-[14px] font-semibold tabular-nums text-amber-700">{money(m.diff, lang, m.currency)}</p>
              <div className="flex w-56 flex-wrap justify-end gap-3">
                <SourceLink document_id={m.document_id} locator={m.locator}>{t("dh.src.report")}</SourceLink>
                {m.workbook_document_id && <SourceLink document_id={m.workbook_document_id} locator={null}>{t("dh.src.excel")}</SourceLink>}
              </div>
            </div>
          ))}
          {unexplained.map((a, i) => (
            <div key={`an${i}`} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3">
              <Badge tone="red"><AlertTriangle className="h-3 w-3" /> {t("dh.unexplained")}</Badge>
              <div className="min-w-[240px] flex-1">
                <p className="text-[13.5px] font-medium text-slate-900">{t("dh.f.unexplained")}</p>
                <p className="text-[12.5px] text-slate-500">
                  <Link href={`/projects/${a.project}`} className="font-semibold text-[#2a78d6] hover:underline">{a.project}</Link> · {period(a.period, lang)} ·{" "}
                  {t("dh.f.anomaly_detail", { act: label("activities", a.activity), excess: money(a.excess, lang, a.currency) })}
                </p>
              </div>
              <p className="w-28 text-right text-[14px] font-semibold tabular-nums text-red-700">+{money(a.excess_usd ?? 0, lang)}</p>
              <div className="flex w-56 justify-end"><SourceLink document_id={a.document_id} locator={a.locator}>{t("dh.src.excel")}</SourceLink></div>
            </div>
          ))}
          {!findingsCount && <p className="px-5 py-6 text-center text-[13px] text-slate-400">{t("dh.no_findings")}</p>}
        </div>
      </Card>

      <div className="grid gap-6 xl:grid-cols-5">
        <Card title={t("dh.anomalies")} subtitle={t("dh.anomalies_sub")} className="xl:col-span-3" bodyClass="px-0 pb-2">
          <div className="divide-y divide-slate-100">
            {anomalies.map((a, i) => <AnomalyRow key={i} a={a} max={maxExcess} />)}
            {!anomalies.length && <p className="px-5 py-6 text-center text-[13px] text-slate-400">{t("dh.no_findings")}</p>}
          </div>
        </Card>

        <div className="space-y-6 xl:col-span-2">
          <Card title={<span className="flex items-center gap-2"><Brain className="h-4 w-4 text-[#1c5cab]" /> {t("dh.models")}</span>} subtitle={t("dh.models_sub")}>
            <div className="space-y-4">
              {Object.entries(data.models).map(([key, m]) => (
                <details key={key} className="group rounded-xl bg-slate-50 p-4 ring-1 ring-slate-100">
                  <summary className="flex cursor-pointer list-none items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-[14px] font-semibold text-slate-900">{t(`dh.m.${key}`)}</p>
                      <p className="text-[12px] text-slate-500">{t(`dh.m.${key}_sub`)}</p>
                      <p className="mt-1 text-[11.5px] text-slate-400">{t("dh.m.detail", { n: m.n_test, train: num(m.n_train, lang) })}</p>
                      <p className="mt-1 flex items-center gap-0.5 text-[11.5px] font-medium text-[#2a78d6]">{t("dh.m.see_errors")} <ChevronRight className="h-3 w-3 transition-transform group-open:rotate-90" /></p>
                    </div>
                    <div className="text-right">
                      <p className="text-[26px] font-semibold leading-none text-[#0c7a0c]">{pct(m.accuracy, lang, 1)}</p>
                      <p className="text-[11px] text-slate-400">{t("dh.m.accuracy")}</p>
                    </div>
                  </summary>
                  <div className="mt-3 border-t border-slate-200 pt-2">
                    <p className="mb-1 text-[11.5px] font-semibold text-slate-500">{t("dh.m.errors")}</p>
                    {m.errors.length ? (
                      <ul className="space-y-0.5 text-[12px] text-slate-600">
                        {m.errors.map((e, i) => (
                          <li key={i}>«{e.label ?? e.question}» → <span className="text-red-700">{e.predicted}</span> <span className="text-slate-400">({t("dh.m.expected")}: {e.expected})</span></li>
                        ))}
                      </ul>
                    ) : <p className="text-[12px] text-slate-400">{t("pj.none")}</p>}
                  </div>
                </details>
              ))}
            </div>
          </Card>
          <Card title={t("dh.templates")} subtitle={t("dh.templates_sub")}>
            <ul className="space-y-2 text-[13px]">
              {data.templates.map((tp, i) => (
                <li key={i} className="flex items-center justify-between gap-3">
                  <span className="flex min-w-0 items-center gap-2"><FileSpreadsheet className="h-4 w-4 shrink-0 text-[#1f3a5f]" /><span className="truncate">{tp.name}</span></span>
                  <Badge tone="green">{t("dh.uses", { n: tp.times_used })}</Badge>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>

      <Card title={t("dh.coverage")} subtitle={t("dh.coverage_sub")} bodyClass="px-0 pb-2">
        <div className="overflow-x-auto">
          <table className="min-w-full text-[12.5px]">
            <thead className="border-y border-slate-100 bg-slate-50/60">
              <tr>
                <Th>{t("pf.col.project")}</Th>
                {DOC_COLS.map(([k]) => <Th key={k} wrap className="text-center">{t(`doc.${k}`)}</Th>)}
                <Th wrap className="text-center">{t("dh.erp_col")}</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {coverage.map((c) => (
                <tr key={c.project} className="hover:bg-slate-50">
                  <Td className="min-w-[240px]"><Link href={`/projects/${c.project}`} className="font-semibold text-[#2a78d6] hover:underline">{c.project}</Link> <span className="text-slate-500">{c.name}</span>
                    {c.origin === "upload" && <Badge tone="violet" className="ml-1.5">{t("pj.uploaded")}</Badge>}</Td>
                  {DOC_COLS.map(([k]) => (
                    <Td key={k} className="text-center">
                      {c.docs[k] ? (
                        <button onClick={() => docs(`${c.project} · ${t(`doc.${k}`)}`, `project=${c.project}&doc_type=${k}`)}
                          className="inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-blue-50 px-1.5 text-[11.5px] font-semibold text-[#1c5cab] hover:bg-[#2a78d6] hover:text-white">
                          {c.docs[k]}
                        </button>
                      ) : <span className="text-slate-300">·</span>}
                    </Td>
                  ))}
                  <Td className="text-center">{c.erp ? <ShieldCheck className="mx-auto h-4 w-4 text-[#0ca30c]" aria-label={t("common.yes")} /> : <span className="text-slate-300">·</span>}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* ---------- what sits behind each number ---------- */}
      <DetailDrawer open={panel?.kind === "docs"} onClose={() => setPanel(null)} title={panel?.kind === "docs" ? panel.title : ""} explain={t("dh.d.docs")}>
        {panel?.kind === "docs" && <DocList query={panel.query} />}
      </DetailDrawer>

      <DetailDrawer open={panel?.kind === "records" || panel?.kind === "lineage"} onClose={() => setPanel(null)}
        title={panel?.kind === "lineage" ? t("dh.q.lineage") : t("dh.records")} explain={panel?.kind === "lineage" ? t("dh.d.lineage") : t("dh.d.records")}>
        <table className="min-w-full text-[13px]">
          <thead className="border-b border-slate-200"><tr><Th>{t("dh.d.what")}</Th><Th>{t("dh.d.from")}</Th><Th right>{t("dh.d.count")}</Th></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {RECORD_KINDS.filter((k) => data.records[k] !== undefined).map((k) => (
              <tr key={k}>
                <Td className="font-medium text-slate-800">{t(`dh.r.${k}`)}</Td>
                <Td className="text-slate-500">{t(`dh.r.${k}_from`)}</Td>
                <Td right className="font-semibold">{num(data.records[k], lang)}</Td>
              </tr>
            ))}
            <tr className="bg-slate-50 font-semibold"><Td>{t("pj.col.total")}</Td><Td /><Td right>{num(data.records_total, lang)}</Td></tr>
          </tbody>
        </table>
        {panel?.kind === "lineage" && <p className="mt-4 rounded-lg bg-blue-50 p-3 text-[12.5px] leading-relaxed text-slate-700">{t("dh.d.lineage_try")}</p>}
      </DetailDrawer>

      <DetailDrawer open={panel?.kind === "workbooks"} onClose={() => setPanel(null)} title={t("dh.q.workbooks")} explain={t("dh.d.workbooks")}>
        <div className="space-y-3">
          {wbItems.map((w) => (
            <div key={w.document_id} className={clsx("rounded-lg p-3 ring-1", w.ok ? "ring-slate-200" : "bg-red-50/50 ring-red-200")}>
              <div className="mb-1.5 flex items-center justify-between gap-3">
                <p className="text-[13px] font-semibold text-slate-900">{w.project ?? "—"} <span className="font-normal text-slate-500">{w.filename}</span></p>
                <SourceLink document_id={w.document_id} locator={null}>{t("common.source")}</SourceLink>
              </div>
              <CheckList checks={w.checks} />
            </div>
          ))}
        </div>
      </DetailDrawer>

      <DetailDrawer open={panel?.kind === "reports"} onClose={() => setPanel(null)} title={t("dh.q.reports")} explain={t("dh.d.reports")}>
        <table className="min-w-full text-[13px]">
          <thead className="border-b border-slate-200"><tr><Th>{t("pf.col.project")}</Th><Th>{t("pj.col.month")}</Th><Th right>{t("dh.d.report_says")}</Th><Th right>{t("dh.d.excel_says")}</Th><Th /></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {repItems.map((m, i) => {
              const ok = m.ok;
              return (
                <tr key={i} className={ok ? "" : "bg-amber-50/60"}>
                  <Td className="whitespace-nowrap font-semibold text-slate-800">{m.project}</Td>
                  <Td className="whitespace-nowrap text-slate-600">{period(m.period, lang)}</Td>
                  <Td right>{money(m.reported, lang, m.currency)}</Td>
                  <Td right>{money(m.workbook, lang, m.currency)}</Td>
                  <Td className="whitespace-nowrap">
                    {ok ? <CheckCircle2 className="inline h-4 w-4 text-[#0ca30c]" aria-label={t("pj.all_ok")} /> : <Badge tone="amber">{t("dh.d.differs")}</Badge>}{" "}
                    <SourceLink document_id={m.document_id} locator={m.locator}>PDF</SourceLink>
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </DetailDrawer>

      <DetailDrawer open={panel?.kind === "erp"} onClose={() => setPanel(null)} title={t("dh.q.erp")} explain={t("dh.d.erp")}>
        <div className="mb-4 grid grid-cols-3 gap-3 text-center">
          <div className="rounded-lg bg-slate-50 p-3"><p className="text-[20px] font-semibold text-slate-900">{num(erp.erp_transactions ?? 0, lang)}</p><p className="text-[11.5px] text-slate-500">{t("dh.d.erp_rows")}</p></div>
          <div className="rounded-lg bg-slate-50 p-3"><p className="text-[20px] font-semibold text-slate-900">{erp.matched}/{erp.cells}</p><p className="text-[11.5px] text-slate-500">{t("dh.d.erp_cells")}</p></div>
          <div className="rounded-lg bg-slate-50 p-3"><p className="text-[20px] font-semibold text-slate-900">{erp.projects}</p><p className="text-[11.5px] text-slate-500">{t("dh.d.erp_projects")}</p></div>
        </div>
        <div className="-mx-5 divide-y divide-slate-100">
          {erp.discrepancies.map((d, i) => <ErpFinding key={i} d={d} />)}
        </div>
      </DetailDrawer>
    </div>
  );
}
