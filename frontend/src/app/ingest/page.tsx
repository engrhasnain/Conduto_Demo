"use client";

import clsx from "clsx";
import {
  ArrowRight, CheckCircle2, ChevronDown, Download, FileSearch, FileSpreadsheet, FileText, GanttChart, HelpCircle, History, Loader2,
  RotateCcw, ScanLine, ShieldCheck, Sparkles, UploadCloud, XCircle,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useApp } from "@/components/providers";
import { Badge, Card, PageHeader, Td, Th } from "@/components/ui";
import { api, fileUrl } from "@/lib/api";
import { date, money, num, pct, period } from "@/lib/format";
import { invalidateAll, useApi } from "@/lib/useApi";

/* eslint-disable @typescript-eslint/no-explicit-any */
type Preview = Record<string, any>;
interface Job { id: number; filename: string; status: string; file_kind: string; ai_used: boolean; preview: Preview; result: Preview | null }
interface Sample { filename: string; kind: string; size: number; description: Record<string, string> }
interface JobRow { id: number; filename: string; status: string; file_kind: string; project_code: string | null; created_at: string }

const KIND_ICON: Record<string, typeof FileText> = { cost_workbook: FileSpreadsheet, legacy_workbook: FileSpreadsheet, change_order_pdf: FileText, document_pdf: FileText, schedule_xml: GanttChart, scanned_pdf: ScanLine };
const WORKBOOK = new Set(["cost_workbook", "legacy_workbook"]);
const PDF = new Set(["change_order_pdf", "document_pdf"]);
const MIN_ANALYZE_MS = 1600; // long enough to see what the system is doing
const MAX_UPLOAD_BYTES = 4 * 1024 * 1024; // same limit as the API (the hosting rejects larger requests)

/* ---------------------------------------------------------------- guide */

function Guide({ stage }: { stage: number }) {
  const { t } = useApp();
  const steps = [
    { icon: UploadCloud, k: "in.g1" },
    { icon: FileSearch, k: "in.g2" },
    { icon: ShieldCheck, k: "in.g3" },
    { icon: CheckCircle2, k: "in.g4" },
  ];
  return (
    <ol className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {steps.map((s, i) => {
        const done = i < stage, now = i === stage;
        return (
          <li key={s.k} className={clsx("flex gap-3 rounded-xl p-3.5 ring-1 transition-colors",
            now ? "bg-[#132a45] text-white ring-[#132a45]" : done ? "bg-emerald-50 ring-emerald-200" : "bg-white ring-black/[0.07]")}>
            <span className={clsx("flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[13px] font-semibold",
              now ? "bg-white/15 text-white" : done ? "bg-[#0ca30c] text-white" : "bg-slate-100 text-slate-500")}>
              {done ? <CheckCircle2 className="h-4 w-4" /> : i + 1}
            </span>
            <div className="min-w-0">
              <p className={clsx("text-[13.5px] font-semibold", now ? "text-white" : "text-slate-900")}>{t(`${s.k}.title`)}</p>
              <p className={clsx("mt-0.5 text-[12px] leading-snug", now ? "text-sky-100/90" : "text-slate-500")}>{t(`${s.k}.body`)}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

function Why() {
  const { t } = useApp();
  return (
    <details className="group rounded-xl bg-white ring-1 ring-black/[0.07]">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-[13.5px] font-semibold text-slate-800">
        <HelpCircle className="h-4 w-4 text-[#2a78d6]" /> {t("in.why.title")}
        <ChevronDown className="ml-auto h-4 w-4 text-slate-400 transition-transform group-open:rotate-180" />
      </summary>
      <div className="grid gap-4 border-t border-slate-100 px-4 py-4 md:grid-cols-3">
        {["in.why.1", "in.why.2", "in.why.3"].map((k) => (
          <div key={k}>
            <p className="text-[13px] font-semibold text-slate-900">{t(`${k}.title`)}</p>
            <p className="mt-1 text-[12.5px] leading-relaxed text-slate-600">{t(`${k}.body`)}</p>
          </div>
        ))}
      </div>
    </details>
  );
}

/* ---------------------------------------------------------------- small pieces */

function Confidence({ v }: { v: number }) {
  const color = v >= 0.9 ? "bg-[#0ca30c]" : v >= 0.7 ? "bg-[#fab219]" : "bg-[#d03b3b]";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 rounded-full bg-slate-100"><div className={clsx("h-1.5 rounded-full", color)} style={{ width: `${Math.max(v, 0.04) * 100}%` }} /></div>
      <span className="w-9 text-right text-[11.5px] tabular-nums text-slate-500">{Math.round(v * 100)}%</span>
    </div>
  );
}

function useCheckText() {
  const { t, lang } = useApp();
  const fmt = (v: any) => (typeof v === "number" ? num(v, lang, Number.isInteger(v) ? 0 : 2) : Array.isArray(v) ? v.join(", ") : v ?? "");
  return (c: any) => {
    const params = Object.fromEntries(Object.entries(c.params ?? {}).map(([k, v]) => [k, fmt(v)]));
    if (c.code === "not_duplicate" && !c.ok) { params.code = params.code ?? ""; params.number = params.number ? ` ${params.number}` : ""; }
    return t(`chk.${c.code}.${c.ok ? "ok" : "fail"}`, params);
  };
}

function Checks({ checks }: { checks: any[] }) {
  const text = useCheckText();
  return (
    <ul className="space-y-1.5">
      {checks.map((c, i) => (
        <li key={i} className="flex items-start gap-2 text-[13px]">
          {c.ok ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#0ca30c]" /> : <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-[#d03b3b]" />}
          <span className={c.ok ? "text-slate-700" : "font-medium text-red-800"}>{text(c)}</span>
        </li>
      ))}
    </ul>
  );
}

function RawGrid({ raw }: { raw: Preview }) {
  const { lang } = useApp();
  if (!raw?.rows) return null;
  return (
    <div className="overflow-x-auto rounded-lg ring-1 ring-slate-200">
      <p className="border-b border-slate-200 bg-slate-50 px-2 py-1 text-[11px] text-slate-500">«{raw.sheet}»</p>
      <table className="min-w-full text-[11.5px]">
        <tbody>
          {raw.rows.map((r: any) => (
            <tr key={r.row} className={r.header ? "bg-amber-50 font-semibold" : ""}>
              <td className="border-r border-b border-slate-100 bg-slate-50 px-1.5 text-right text-slate-400">{r.row}</td>
              {r.cells.map((v: any, i: number) => (
                <td key={i} className={clsx("max-w-[150px] truncate border-b border-r border-slate-100 px-1.5 py-1", typeof v === "number" && "text-right tabular-nums")}>
                  {v === null ? "" : typeof v === "number" ? num(v, lang, Number.isInteger(v) ? 0 : 2) : String(v)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ActivitySelect({ value, onChange }: { value: string | null; onChange: (v: string) => void }) {
  const { t, label, meta } = useApp();
  const acts = Object.keys(meta?.activities ?? {});
  return (
    <select value={value ?? ""} onChange={(e) => onChange(e.target.value)}
      className={clsx("w-full max-w-[260px] rounded-md border px-1.5 py-1 text-[12.5px]", value ? "border-slate-200 bg-white" : "border-red-300 bg-red-50")}>
      <option value="">{t("in.unmapped")}</option>
      {acts.map((a) => <option key={a} value={a}>{label("activities", a)}</option>)}
    </select>
  );
}

function MethodBadge({ method, manual }: { method: string; manual: boolean }) {
  const { t } = useApp();
  const m = manual ? "manual" : method;
  return (
    <Badge tone={m === "ai" ? "blue" : m === "template" ? "green" : m === "ml" ? "violet" : m === "fuzzy" ? "amber" : "neutral"}>
      {m === "ai" && <Sparkles className="h-3 w-3" />}{t(`in.method.${m}`)}
    </Badge>
  );
}

function MappingTable({ rows, overrides, setOverride, showAmounts }: { rows: any[]; overrides: Record<string, string>; setOverride: (l: string, c: string) => void; showAmounts?: boolean }) {
  const { t, lang } = useApp();
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-[12.5px]">
        <thead className="border-b border-slate-200">
          <tr><Th>{t("in.col.label")}</Th><Th>{t("in.col.target")}</Th><Th>{t("in.col.confidence")}</Th><Th>{t("in.col.method")}</Th>{showAmounts && <Th right>{t("in.np.cost")}</Th>}</tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((m) => (
            <tr key={m.label}>
              <Td className="font-mono text-[12px] text-slate-700">{m.label}{m.note_in_file && <p className="font-sans text-[11px] text-slate-400">{m.note_in_file}</p>}</Td>
              <Td><ActivitySelect value={overrides[m.label] ?? m.code} onChange={(v) => setOverride(m.label, v)} /></Td>
              <Td><Confidence v={overrides[m.label] ? 1 : m.confidence} /></Td>
              <Td><MethodBadge method={m.method} manual={!!overrides[m.label]} /></Td>
              {showAmounts && <Td right className="whitespace-nowrap">{num(m.budget, lang)} → <b>{num(m.actual, lang)}</b></Td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Section({ title, children, open = false }: { title: string; children: React.ReactNode; open?: boolean }) {
  return (
    <details open={open} className="group rounded-xl bg-white ring-1 ring-black/[0.07]">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-5 py-3.5 text-[14px] font-semibold text-slate-800">
        <ChevronDown className="h-4 w-4 text-slate-400 transition-transform group-open:rotate-180" /> {title}
      </summary>
      <div className="border-t border-slate-100 px-5 py-4">{children}</div>
    </details>
  );
}

/* ---------------------------------------------------------------- analyzing */

function Analyzing({ name }: { name: string }) {
  const { t } = useApp();
  const msgs = ["in.an.1", "in.an.2", "in.an.3", "in.an.4"];
  const [i, setI] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setI((x) => Math.min(x + 1, msgs.length - 1)), 450);
    return () => clearInterval(id);
  }, [msgs.length]);
  return (
    <Card>
      <div className="flex flex-col items-center gap-4 py-8 text-center">
        <div className="relative">
          <div className="h-14 w-14 animate-spin rounded-full border-4 border-slate-100 border-t-[#2a78d6]" />
          <FileSearch className="absolute inset-0 m-auto h-6 w-6 text-[#132a45]" />
        </div>
        <p className="text-[15px] font-semibold text-slate-900">{name}</p>
        <ul className="space-y-1 text-[13px]">
          {msgs.map((k, j) => (
            <li key={k} className={clsx("flex items-center justify-center gap-2 transition-opacity", j <= i ? "opacity-100" : "opacity-30")}>
              {j < i ? <CheckCircle2 className="h-3.5 w-3.5 text-[#0ca30c]" /> : j === i ? <Loader2 className="h-3.5 w-3.5 animate-spin text-[#2a78d6]" /> : <span className="h-3.5 w-3.5" />}
              <span className={j === i ? "font-medium text-slate-800" : "text-slate-500"}>{t(k)}</span>
            </li>
          ))}
        </ul>
      </div>
    </Card>
  );
}

/* ---------------------------------------------------------------- summary of what was understood */

function Summary({ job, mapped, total }: { job: Job; mapped: number; total: number }) {
  const { t, lang, label, country } = useApp();
  const pv = job.preview;
  const Icon = KIND_ICON[pv.kind] ?? FileText;
  const proj = pv.project ? `${pv.project.code} · ${pv.project.name}` : t("in.project_none");
  const field = (f: string) => pv.fields?.find((x: any) => x.field === f)?.value;
  let headline = "";
  const bullets: string[] = [];

  if (pv.kind === "cost_workbook") {
    headline = t("in.sum.cost", { project: proj });
    if (pv.periods?.count) bullets.push(t("in.sum.cost_months", { n: pv.periods.count, first: period(pv.periods.first, lang), last: period(pv.periods.last, lang) }));
    if (pv.records) bullets.push(t("in.sum.cost_records", { cost: num(pv.records.cost_values, lang), budget: pv.records.budget_lines, progress: pv.records.progress_points }));
    bullets.push(t("in.sum.lines", { mapped, total }));
  } else if (pv.kind === "legacy_workbook" && pv.new_project) {
    const np = pv.new_project;
    headline = t("in.sum.legacy", { name: np.name });
    bullets.push(`${country(np.country)} · ${label("terrains", np.terrain)}${np.diameter_in ? ` · ${t("bm.scope_v", { d: np.diameter_in, km: num(np.length_km, lang, 1) })}` : ""} · ${period(np.start_period, lang)} → ${period(np.finish_period, lang)}`);
    bullets.push(t("in.sum.legacy_money", { contract: money(np.contract_value, lang, np.currency), budget: money(np.budget, lang, np.currency), final: money(np.final_cost, lang, np.currency) }));
    bullets.push(t("in.sum.legacy_margin", { bid: pct(np.bid_margin_pct, lang), final: pct(np.final_margin_pct, lang) }));
    bullets.push(t("in.sum.lines", { mapped, total }));
    if (np.code) bullets.push(t("in.sum.legacy_code", { code: np.code }));
  } else if (pv.kind === "change_order_pdf") {
    headline = t("in.sum.co", { number: field("co_number") ?? "?", project: proj, amount: money(field("amount"), lang, field("currency") || "USD", false) });
    const title = (lang === "en" && field("title_en")) || field("title");
    if (title) bullets.push(String(title));
    if (field("cause")) bullets.push(`${t("in.f.cause")}: ${label("co_causes", field("cause"))}`);
    if (field("submitted_date")) bullets.push(`${t("in.f.submitted_date")}: ${date(field("submitted_date"), lang)}`);
    const g = pv.fields.filter((f: any) => f.grounded !== null && f.grounded !== undefined);
    if (g.length) bullets.push(t("in.sum.grounded", { n: g.filter((f: any) => f.grounded).length, total: g.length }));
  } else if (pv.kind === "document_pdf") {
    headline = t("in.sum.doc", { type: t(`doc.${pv.doc_type ?? "other"}`), project: proj });
    bullets.push(t("in.sum.pages", { n: pv.pages }));
  } else if (pv.kind === "schedule_xml") {
    headline = t("in.sum.schedule", { project: proj });
    if (pv.forecast_finish?.old) bullets.push(t("in.ff", { old: period(pv.forecast_finish.old, lang), new: period(pv.forecast_finish.new, lang) }));
    bullets.push(t("in.sum.tasks", { n: pv.changes?.length ?? 0, total: pv.tasks?.length ?? 0 }));
    if (pv.status_date) bullets.push(`${t("in.sum.status_date")}: ${date(String(pv.status_date).slice(0, 10), lang)}`);
  } else if (pv.kind === "scanned_pdf") {
    headline = t("in.scan.title");
    bullets.push(t("in.scan.body", { pages: pv.pages, lo: num(pv.ocr_estimate_usd?.[0], lang, 2), hi: num(pv.ocr_estimate_usd?.[1], lang, 2) }));
    bullets.push(t("in.scan.with_ai"));
  } else {
    headline = t("in.sum.failed");
    bullets.push(pv.error ?? t(`in.kind.${pv.kind}`));
  }

  const engine = pv.engine === "template" && pv.template ? t("in.engine.template", { name: pv.template.name, n: pv.template.times_used })
    : pv.engine === "ai" ? t("in.engine.ai") : pv.engine === "ml" ? t("in.engine.ml") : pv.engine === "needs_ai" ? t("in.engine.needs_ai")
    : pv.engine === "ai_vision" ? t("in.engine.ai_vision") : PDF.has(pv.kind) ? t("in.engine.rules_pdf") : pv.kind === "schedule_xml" ? t("in.engine.xml") : t("in.engine.rules");

  return (
    <Card>
      <div className="flex items-start gap-4">
        <div className={clsx("rounded-xl p-3", pv.kind === "scanned_pdf" ? "bg-amber-50 text-amber-700" : "bg-blue-50 text-[#1c5cab]")}><Icon className="h-6 w-6" /></div>
        <div className="min-w-0 flex-1">
          <p className="text-[12px] font-medium uppercase tracking-wide text-slate-400">{t("in.understood")} · {t(`in.kind.${pv.kind}`)}</p>
          <p className="mt-1 text-[18px] font-semibold leading-snug text-slate-900">{headline}</p>
          <ul className="mt-2 space-y-1 text-[13.5px] text-slate-600">
            {bullets.map((b, i) => <li key={i} className="flex gap-2"><span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-slate-400" />{b}</li>)}
          </ul>
          <p className="mt-3 flex flex-wrap items-center gap-2 text-[12px] text-slate-500">
            <span className="break-all">{job.filename}</span>
            {pv.engine && <Badge tone={pv.engine === "template" ? "green" : pv.engine === "needs_ai" ? "amber" : "blue"}>{engine}</Badge>}
            <a href={fileUrl(`/api/ingest/jobs/${job.id}/file`)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-[#2a78d6] hover:underline"><Download className="h-3 w-3" /> {t("in.download")}</a>
          </p>
        </div>
      </div>
    </Card>
  );
}

/* ---------------------------------------------------------------- job */

function JobView({ job, onImported, onDiscard }: { job: Job; onImported: (j: Job) => void; onDiscard: () => void }) {
  const { t, lang, label } = useApp();
  const checkText = useCheckText();
  const pv = job.preview;
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [importing, setImporting] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const setOverride = (l: string, c: string) => setOverrides((o) => ({ ...o, [l]: c }));
  const rows: any[] = (pv.row_mapping ?? []).map((m: any) => ({ ...m, code: overrides[m.label] ?? m.code }));
  const allMapped = rows.every((m) => m.code);
  const mapped = rows.filter((m) => m.code).length;
  const isWb = WORKBOOK.has(pv.kind);
  const checks: any[] = (pv.checks ?? []).map((c: any) => c.code === "rows_mapped" && isWb ? { ...c, ok: allMapped, params: { ...c.params, mapped } } : c);
  const ready = isWb ? (pv.ready || (allMapped && checks.filter((c) => c.code !== "rows_mapped").every((c) => c.ok))) : pv.ready;

  // what a person should look at: unsure lines, failed checks, values not found word for word
  const unsure = isWb ? (pv.row_mapping ?? []).filter((m: any) => !m.code || m.confidence < 0.8 || m.note === "combined") : [];
  const failed = checks.filter((c) => !c.ok && !(isWb && c.code === "rows_mapped"));
  const doubtful = PDF.has(pv.kind) ? (pv.fields ?? []).filter((f: any) => f.value !== null && f.value !== "" && (f.grounded === false || f.confidence < 0.7)) : [];

  async function confirm() {
    setImporting(true);
    setErr(null);
    try {
      const r = await api<{ result: Preview; job: Job }>(`/api/ingest/jobs/${job.id}/confirm`, { method: "POST", body: JSON.stringify({ row_mapping: overrides }) });
      invalidateAll();
      onImported(r.job);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setImporting(false);
    }
  }

  if (job.status === "imported" && job.result) return <Done res={job.result} onNew={onDiscard} />;

  const fieldValue = (f: any) => f.field === "submitted_date" ? date(f.value, lang)
    : f.field === "amount" ? money(f.value, lang, pv.fields.find((x: any) => x.field === "currency")?.value || "USD", false)
    : f.field === "activity_code" ? label("activities", f.value)
    : f.field === "cause" ? label("co_causes", f.value)
    : f.field === "status" ? label("co_status", f.value)
    : f.field === "doc_type" ? t(`doc.${f.value}`)
    : typeof f.value === "boolean" ? t(f.value ? "common.yes" : "common.no") : String(f.value);

  const canImport = job.status === "preview";

  return (
    <div className="space-y-4">
      <Summary job={job} mapped={mapped} total={rows.length} />

      {canImport && (
        unsure.length || failed.length || doubtful.length ? (
          <Card className="ring-amber-200" title={<span className="flex items-center gap-2 text-amber-900"><ShieldCheck className="h-4 w-4 text-amber-600" /> {t("in.check.title")}</span>} subtitle={t("in.check.sub")}>
            <div className="space-y-4">
              {unsure.length > 0 && (
                <div>
                  <p className="mb-2 text-[13px] font-semibold text-slate-800">{t("in.check.lines", { n: unsure.length })}</p>
                  <div className="divide-y divide-slate-100 rounded-lg ring-1 ring-slate-200">
                    {unsure.map((m: any) => (
                      <div key={m.label} className="grid items-center gap-2 px-3 py-2 sm:grid-cols-[minmax(0,1fr)_260px_90px]">
                        <div className="min-w-0">
                          <p className="truncate font-mono text-[12.5px] text-slate-800">«{m.label}»</p>
                          <p className="text-[11.5px] text-slate-500">
                            {m.note === "combined" ? t("in.note.combined") : m.note === "not_activity" ? t("in.note.not_activity")
                              : m.code ? t("in.check.guess") : t("in.check.no_guess")}
                            {!overrides[m.label] && m.alternatives?.length > 0 && ` ${t("in.alternatives")}: ${m.alternatives.slice(0, 2).map((a: [string, number]) => `${label("activities", a[0])} (${Math.round(a[1] * 100)}%)`).join(", ")}`}
                          </p>
                        </div>
                        <ActivitySelect value={overrides[m.label] ?? m.code} onChange={(v) => setOverride(m.label, v)} />
                        <Confidence v={overrides[m.label] ? 1 : m.confidence} />
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {doubtful.length > 0 && (
                <div>
                  <p className="mb-2 text-[13px] font-semibold text-slate-800">{t("in.check.values", { n: doubtful.length })}</p>
                  <ul className="space-y-1 text-[13px]">
                    {doubtful.map((f: any) => <li key={f.field} className="flex gap-2"><span className="text-slate-500">{t(`in.f.${f.field}`)}:</span> <b className="text-slate-900">{fieldValue(f)}</b></li>)}
                  </ul>
                </div>
              )}
              {failed.length > 0 && (
                <ul className="space-y-1.5">
                  {failed.map((c, i) => <li key={i} className="flex items-start gap-2 text-[13px] font-medium text-red-800"><XCircle className="mt-0.5 h-4 w-4 shrink-0 text-[#d03b3b]" /> {checkText(c)}</li>)}
                </ul>
              )}
            </div>
          </Card>
        ) : (
          <div className="flex items-center gap-3 rounded-xl bg-emerald-50 p-4 text-[13.5px] text-emerald-900 ring-1 ring-emerald-200">
            <CheckCircle2 className="h-5 w-5 shrink-0 text-[#0ca30c]" /> {t("in.check.all_ok", { n: checks.length })}
          </div>
        )
      )}

      {canImport && (
        <div className="sticky bottom-3 z-10 flex flex-wrap items-center gap-3 rounded-xl bg-white/95 p-3 shadow-lg ring-1 ring-black/[0.08] backdrop-blur">
          <button onClick={confirm} disabled={!ready || importing}
            className="inline-flex items-center gap-2 rounded-lg bg-[#132a45] px-4 py-2 text-[14px] font-medium text-white disabled:opacity-40">
            {importing ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
            {importing ? t("in.importing") : t("in.confirm")}
          </button>
          <button onClick={onDiscard} className="rounded-lg px-3 py-2 text-[13px] text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50">{t("in.discard")}</button>
          <span className={clsx("text-[12.5px]", ready ? "text-slate-500" : "text-amber-700")}>{ready ? t("in.nothing_saved") : t("in.not_ready")}</span>
          {err && <span className="text-[13px] text-red-700">{err === "network" ? t("shell.api_down") : err}</span>}
        </div>
      )}

      {job.status !== "preview" && pv.kind !== "scanned_pdf" && (
        <div className="flex items-center gap-3">
          <button onClick={onDiscard} className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-[13px] text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"><RotateCcw className="h-3.5 w-3.5" /> {t("in.another")}</button>
        </div>
      )}

      {pv.kind === "scanned_pdf" && (
        <Card title={t("in.d.file")}>
          <iframe title={job.filename} src={fileUrl(`/api/ingest/jobs/${job.id}/file`)} className="h-[460px] w-full rounded-lg ring-1 ring-slate-200" />
          <button onClick={onDiscard} className="mt-3 inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-[13px] text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"><RotateCcw className="h-3.5 w-3.5" /> {t("in.another")}</button>
        </Card>
      )}

      {isWb && (
        <>
          <Section title={t("in.d.mapping", { n: rows.length })}>
            <p className="mb-3 text-[12.5px] text-slate-500">{t("in.d.mapping_sub")}</p>
            <MappingTable rows={pv.row_mapping} overrides={overrides} setOverride={setOverride} showAmounts={pv.kind === "legacy_workbook"} />
            {pv.cost_type_mapping?.length > 0 && (
              <div className="mt-3 flex flex-wrap items-center gap-1.5 text-[12px] text-slate-600">
                <span className="font-semibold">{t("in.cost_types")}:</span>
                {pv.cost_type_mapping.map((c: any) => <Badge key={c.label}>{c.label} → {c.code ? label("cost_types", c.code) : "?"}</Badge>)}
              </div>
            )}
          </Section>
          <Section title={t("in.d.file")}><RawGrid raw={pv.raw_preview} /></Section>
        </>
      )}

      {PDF.has(pv.kind) && (
        <>
          <Section title={t("in.d.fields")}>
            <table className="min-w-full text-[12.5px]">
              <thead className="border-b border-slate-200"><tr><Th>{t("in.d.field")}</Th><Th>{t("in.d.value")}</Th><Th>{t("in.col.confidence")}</Th><Th>{t("in.col.verified")}</Th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {pv.fields.filter((f: any) => f.value !== null && f.value !== "").map((f: any) => (
                  <tr key={f.field}>
                    <Td className="text-slate-500">{t(`in.f.${f.field}`)}</Td>
                    <Td className="min-w-[220px] font-medium text-slate-900">{fieldValue(f)}</Td>
                    <Td><Confidence v={f.confidence} /></Td>
                    <Td>{f.grounded ? <span title={t("in.grounded")}><ShieldCheck className="h-4 w-4 text-[#0ca30c]" /></span> : f.grounded === false ? <XCircle className="h-4 w-4 text-amber-500" /> : null}</Td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-2 text-[12px] text-slate-400">{t("in.grounded")}</p>
          </Section>
          <Section title={t("in.d.file")}>
            <pre className="max-h-[420px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 font-sans text-[12px] leading-relaxed text-slate-700">{pv.text_preview}</pre>
          </Section>
        </>
      )}

      {pv.kind === "schedule_xml" && (
        <Section title={t("in.changes")} open>
          {pv.changes?.length ? (
            <table className="min-w-full text-[12.5px]">
              <thead className="border-b border-slate-200"><tr><Th>{t("in.col.task")}</Th><Th>{t("in.col.old")}</Th><Th>{t("in.col.new")}</Th><Th right>{t("in.col.delta")}</Th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {pv.changes.map((c: any) => (
                  <tr key={c.uid}><Td>{c.activity ? label("activities", c.activity) : c.name}</Td><Td>{date(c.old_finish, lang)}</Td><Td className="font-medium">{date(c.new_finish, lang)}</Td>
                    <Td right className={c.delta_days > 0 ? "font-semibold text-amber-700" : "text-emerald-700"}>{c.delta_days > 0 ? "+" : ""}{c.delta_days}</Td></tr>
                ))}
              </tbody>
            </table>
          ) : <p className="text-[13px] text-slate-400">{t("pj.none")}</p>}
        </Section>
      )}

      {checks.length > 0 && pv.kind !== "scanned_pdf" && (
        <Section title={t("in.d.checks", { ok: checks.filter((c) => c.ok).length, n: checks.length })}>
          <Checks checks={checks} />
          {pv.skipped?.length > 0 && <p className="mt-3 text-[12.5px] text-slate-500">{t("in.skipped", { n: pv.skipped.length })}</p>}
        </Section>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- done */

function Done({ res, onNew }: { res: Preview; onNew: () => void }) {
  const { t, lang } = useApp();
  const keys = ["forecast_margin_pct", "pending_co_usd", "delay_months", "eac_usd", "health"];
  const fmtK = (k: string, v: any) => k === "forecast_margin_pct" ? pct(v, lang) : k.endsWith("_usd") ? money(v, lang) : k === "health" ? t(`health.${v}`) : String(v ?? "–");
  return (
    <Card>
      <div className="space-y-4">
        <div className="flex items-start gap-3">
          <div className="rounded-full bg-emerald-50 p-2"><CheckCircle2 className="h-6 w-6 text-[#0ca30c]" /></div>
          <div>
            <p className="text-[18px] font-semibold text-slate-900">{t("in.done")}</p>
            <p className="text-[13px] text-slate-500">{t("in.done_sub")}</p>
          </div>
        </div>
        {res.before && res.after && (
          <div>
            <p className="mb-2 text-[13px] font-semibold text-slate-700">{t("in.impact", { code: res.project_code })}</p>
            <table className="text-[13px]">
              <thead><tr><Th /><Th right>{t("in.before_lbl")}</Th><Th /><Th right>{t("in.after_lbl")}</Th></tr></thead>
              <tbody>
                {keys.map((k) => {
                  const changed = JSON.stringify(res.before[k]) !== JSON.stringify(res.after[k]);
                  return (
                    <tr key={k} className={changed ? "bg-amber-50" : ""}>
                      <Td className="text-slate-500">{t(`in.kpi.${k}`)}</Td><Td right>{fmtK(k, res.before[k])}</Td>
                      <Td className="text-slate-300"><ArrowRight className="h-3.5 w-3.5" /></Td>
                      <Td right className={changed ? "font-semibold text-slate-900" : ""}>{fmtK(k, res.after[k])}</Td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {res.after && !res.before && (
          <p className="text-[13px] text-slate-700">{res.project_code} · {t("in.kpi.forecast_margin_pct")}: <b>{pct(res.after.forecast_margin_pct, lang)}</b></p>
        )}
        {res.benchmark_projects && <p className="text-[13px] text-slate-700">{t("in.bench_count", res.benchmark_projects)}</p>}
        {res.template?.created && <p className="rounded-lg bg-emerald-50 p-2.5 text-[13px] text-emerald-900 ring-1 ring-emerald-200">{t("in.template_saved")}</p>}
        {res.template && !res.template.created && res.template.name && <p className="text-[13px] text-slate-600">{t("in.template_used", { name: res.template.name, n: res.template.times_used })}</p>}
        <div className="flex flex-wrap gap-2">
          <Link href={`/projects/${res.project_code}`} className="inline-flex items-center gap-1.5 rounded-lg bg-[#132a45] px-3 py-1.5 text-[13px] font-medium text-white">{t("in.goto_project")} <ArrowRight className="h-3.5 w-3.5" /></Link>
          {res.benchmark_projects && <Link href="/benchmarks" className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[13px] font-medium text-[#2a78d6] ring-1 ring-slate-200">{t("in.goto_bench")}</Link>}
          <button onClick={onNew} className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[13px] text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"><RotateCcw className="h-3.5 w-3.5" /> {t("in.another")}</button>
        </div>
      </div>
    </Card>
  );
}

/* ---------------------------------------------------------------- page */

export default function IngestPage() {
  const { t, lang } = useApp();
  const { data: samples } = useApi<Sample[]>("/api/ingest/samples");
  const { data: history } = useApi<JobRow[]>("/api/ingest/jobs");
  const [job, setJob] = useState<Job | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [drag, setDrag] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const topRef = useRef<HTMLDivElement>(null);

  async function run(name: string, fn: () => Promise<Job>) {
    setBusy(name);
    setErr(null);
    setJob(null);
    topRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    try {
      const [j] = await Promise.all([fn(), new Promise((r) => setTimeout(r, MIN_ANALYZE_MS))]);
      setJob(j);
      invalidateAll();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  const analyzeSample = (f: string) => run(f, () => api<Job>(`/api/ingest/samples/${encodeURIComponent(f)}`, { method: "POST" }));
  const upload = (file: File) => {
    if (file.size > MAX_UPLOAD_BYTES) {
      setJob(null);
      setErr(t("in.too_big", { mb: (file.size / 1024 / 1024).toFixed(1) }));
      return;
    }
    const fd = new FormData();
    fd.append("file", file);
    return run(file.name, () => api<Job>("/api/ingest/upload", { method: "POST", body: fd }));
  };
  const openJob = (id: number) => {
    setErr(null);
    void api<Job>(`/api/ingest/jobs/${id}`).then((j) => { setJob(j); topRef.current?.scrollIntoView({ behavior: "smooth" }); }).catch((e: Error) => setErr(e.message));
  };

  // deep link: /ingest?job=<id> reopens an analyzed or imported file
  useEffect(() => {
    const id = Number(new URLSearchParams(window.location.search).get("job"));
    if (id) void api<Job>(`/api/ingest/jobs/${id}`).then(setJob).catch(() => undefined);
  }, []);

  const stage = busy ? 1 : job ? (job.status === "imported" ? 4 : 2) : 0;

  return (
    <div className="space-y-5">
      <PageHeader title={t("in.title")} subtitle={t("in.sub")} />
      <div ref={topRef} className="scroll-mt-20"><Guide stage={stage} /></div>
      <Why />

      {busy && <Analyzing name={busy} />}
      {err && (
        <div className="flex flex-wrap items-center gap-3 rounded-xl bg-red-50 p-4 text-[13px] text-red-800 ring-1 ring-red-200">
          <XCircle className="h-4 w-4" /> {err === "network" ? t("shell.api_down") : err}
          <button onClick={() => setErr(null)} className="ml-auto rounded-md bg-white px-2.5 py-1 text-[12px] ring-1 ring-red-200">{t("common.close")}</button>
        </div>
      )}
      {job && !busy && <JobView key={job.id} job={job} onImported={setJob} onDiscard={() => setJob(null)} />}

      {!job && !busy && (
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
          <div>
            <p className="mb-2 text-[13px] font-semibold text-slate-800">{t("in.samples")}</p>
            <p className="mb-3 text-[12.5px] text-slate-500">{t("in.samples_sub")}</p>
            <div className="grid gap-3 md:grid-cols-2">
              {samples?.map((s) => {
                const Icon = KIND_ICON[s.kind] ?? FileText;
                return (
                  <div key={s.filename} className="flex flex-col rounded-xl bg-white p-4 ring-1 ring-black/[0.07] transition-shadow hover:shadow-md">
                    <div className="flex items-start gap-3">
                      <div className={clsx("rounded-lg p-2", s.kind === "scanned_pdf" ? "bg-amber-50 text-amber-700" : "bg-blue-50 text-[#1c5cab]")}><Icon className="h-5 w-5" /></div>
                      <div className="min-w-0">
                        <p className="text-[14px] font-semibold text-slate-900">{t(`in.kind.${s.kind}`)}</p>
                        <p className="break-all text-[11.5px] text-slate-400">{s.filename}</p>
                      </div>
                    </div>
                    <p className="mt-2 text-[12.5px] leading-relaxed text-slate-600">{s.description[lang]}</p>
                    <p className="mt-2 flex-1 text-[12px] leading-relaxed text-[#1c5cab]">{t(`in.shows.${s.kind}`)}</p>
                    <div className="mt-3 flex items-center gap-3">
                      <button onClick={() => analyzeSample(s.filename)} disabled={!!busy}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-[#132a45] px-3 py-1.5 text-[13px] font-medium text-white disabled:opacity-50">
                        <FileSearch className="h-3.5 w-3.5" /> {t("in.analyze")}
                      </button>
                      <a href={fileUrl(`/api/ingest/samples/${encodeURIComponent(s.filename)}/file`)} className="inline-flex items-center gap-1 text-[12.5px] text-[#2a78d6] hover:underline">
                        <Download className="h-3.5 w-3.5" /> {t("in.download")}
                      </a>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
          <div>
            <p className="mb-2 text-[13px] font-semibold text-slate-800">{t("in.own")}</p>
            <p className="mb-3 text-[12.5px] text-slate-500">{t("in.own_sub")}</p>
            <div
              role="button" tabIndex={0}
              onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
              onDragLeave={() => setDrag(false)}
              onDrop={(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files[0]; if (f) void upload(f); }}
              onClick={() => inputRef.current?.click()}
              onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
              className={clsx("flex min-h-[220px] cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-6 text-center transition-colors", drag ? "border-[#2a78d6] bg-blue-50" : "border-slate-300 bg-white hover:border-[#2a78d6]")}
            >
              <UploadCloud className="h-9 w-9 text-slate-400" />
              <p className="mt-3 text-[14px] font-medium text-slate-700">{t("in.drop")}</p>
              <p className="mt-1 text-[12px] text-slate-400">{t("in.drop_types")}</p>
              <input ref={inputRef} type="file" accept=".xlsx,.xlsm,.pdf,.xml" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) void upload(f); e.target.value = ""; }} />
            </div>
          </div>
        </div>
      )}

      {history && history.length > 0 && (
        <details className="group rounded-xl bg-white ring-1 ring-black/[0.07]">
          <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-[13.5px] font-semibold text-slate-800">
            <History className="h-4 w-4 text-slate-500" /> {t("in.history")} <Badge>{history.length}</Badge>
            <ChevronDown className="ml-auto h-4 w-4 text-slate-400 transition-transform group-open:rotate-180" />
          </summary>
          <div className="overflow-x-auto border-t border-slate-100">
            <table className="min-w-full text-[12.5px]">
              <thead><tr><Th>{t("in.h.file")}</Th><Th>{t("in.h.type")}</Th><Th>{t("pf.col.project")}</Th><Th>{t("in.h.when")}</Th><Th>{t("pj.col.status")}</Th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {history.slice(0, 20).map((h) => (
                  <tr key={h.id} onClick={() => openJob(h.id)} className="cursor-pointer hover:bg-slate-50">
                    <Td className="max-w-[320px] truncate font-medium text-slate-800">{h.filename}</Td>
                    <Td className="text-slate-500">{t(`in.kind.${h.file_kind}`)}</Td>
                    <Td className="text-slate-600">{h.project_code ?? "—"}</Td>
                    <Td className="whitespace-nowrap text-slate-500">{date(h.created_at.slice(0, 10), lang)}</Td>
                    <Td><Badge tone={h.status === "imported" ? "green" : h.status === "failed" ? "red" : h.status === "needs_ai" ? "violet" : "amber"}>{t(`in.status.${h.status}`)}</Badge></Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </div>
  );
}
