"use client";

import clsx from "clsx";
import { ArrowLeft, ExternalLink, FileSpreadsheet, FileText, GanttChart, X } from "lucide-react";
import { useEffect, useState } from "react";
import { fileUrl } from "@/lib/api";
import { money, num, pct, period } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { SourceRequest, useApp } from "./providers";
import { Badge, Loading, ErrorState } from "./ui";

interface Preview {
  document: { id: number; title: string; filename: string; doc_type: string; project_code: string | null; file_url: string; period: string | null };
  locator: string | null;
  type: "sheet" | "pdf" | "xml" | "file";
  sheet?: string;
  cell?: string;
  value?: unknown;
  columns?: string[];
  grid?: { row: number; header: boolean; cells: { col: string; value: unknown; target: boolean }[] }[];
  page?: number;
  text?: string;
  file_url?: string;
  snippet?: string;
}

interface ActivityLineage {
  project: string;
  activity: string;
  names: Record<string, string>;
  currency: string;
  budget: { cost_type: string; amount: number; origin: string; co_number: string | null; document_id: number | null; locator: string | null }[];
  costs: { period: string; cost_type: string; amount: number; document_id: number | null; locator: string | null }[];
  progress: { period: string; pct: number; planned: number; document_id: number | null; locator: string | null } | null;
}

function fmtCell(v: unknown, lang: "es" | "en" | "pt"): string {
  if (v === null || v === undefined) return "";
  if (typeof v === "number") {
    if (Math.abs(v) < 1.5 && !Number.isInteger(v)) return num(v, lang, 4);
    return num(v, lang, Number.isInteger(v) ? 0 : 2);
  }
  return String(v);
}

function SheetView({ p }: { p: Preview }) {
  const { lang } = useApp();
  return (
    <div className="overflow-x-auto rounded-lg ring-1 ring-slate-200">
      <table className="min-w-full border-collapse text-[12px]">
        <thead>
          <tr className="bg-slate-100 text-slate-500">
            <th className="w-10 border-b border-r border-slate-200 px-2 py-1" />
            {p.columns?.map((c) => <th key={c} className="border-b border-r border-slate-200 px-2 py-1 font-medium">{c}</th>)}
          </tr>
        </thead>
        <tbody>
          {p.grid?.map((r) => (
            <tr key={r.row} className={r.header ? "bg-[#1f3a5f]/[0.06] font-semibold" : ""}>
              <td className="border-r border-b border-slate-200 bg-slate-50 px-2 py-1 text-right text-slate-400">{r.row}</td>
              {r.cells.map((c) => (
                <td key={c.col} className={clsx(
                  "max-w-[180px] truncate border-b border-r border-slate-200 px-2 py-1",
                  typeof c.value === "number" && "text-right tabular-nums",
                  c.target && "bg-amber-100 font-semibold text-slate-900 outline outline-2 -outline-offset-2 outline-amber-500",
                )} title={fmtCell(c.value, lang)}>
                  {fmtCell(c.value, lang)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PreviewView({ req }: { req: Extract<SourceRequest, { kind: "source" }> }) {
  const { t } = useApp();
  const [showPdf, setShowPdf] = useState(false);
  const { data, error, loading } = useApi<Preview>(`/api/lineage?document_id=${req.document_id}${req.locator ? `&locator=${encodeURIComponent(req.locator)}` : ""}`);
  if (loading && !data) return <Loading />;
  if (error) return <ErrorState message={error} />;
  if (!data) return null;
  const Icon = data.type === "sheet" ? FileSpreadsheet : data.type === "xml" ? GanttChart : FileText;
  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3">
        <div className="rounded-lg bg-slate-100 p-2 text-[#1f3a5f]"><Icon className="h-5 w-5" /></div>
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-slate-900">{data.document.title}</p>
          <p className="truncate text-[12px] text-slate-500">{data.document.filename}</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            <Badge tone="blue">{t(`doc.${data.document.doc_type}`)}</Badge>
            {data.document.project_code && <Badge>{data.document.project_code}</Badge>}
            {data.type === "sheet" && <Badge tone="amber">{t("src.cell", { cell: data.cell ?? "", sheet: data.sheet ?? "" })}</Badge>}
            {data.type === "pdf" && <Badge tone="amber">{t("src.page", { page: data.page ?? 1 })}</Badge>}
            {data.type === "xml" && data.locator && <Badge tone="amber">{data.locator}</Badge>}
          </div>
        </div>
      </div>
      {data.type === "sheet" && <SheetView p={data} />}
      {data.type === "pdf" && (
        <div className="space-y-2">
          <div className="flex justify-end">
            <button onClick={() => setShowPdf((s) => !s)} className="text-[12px] font-medium text-[#2a78d6] hover:underline">
              {showPdf ? t("src.show_text") : t("src.show_pdf")}
            </button>
          </div>
          {showPdf ? (
            <iframe title={data.document.title} src={fileUrl(data.file_url ?? data.document.file_url)} className="h-[65vh] w-full rounded-lg ring-1 ring-slate-200" />
          ) : (
            <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-4 font-sans text-[12.5px] leading-relaxed text-slate-700 ring-1 ring-slate-200">{data.text}</pre>
          )}
        </div>
      )}
      {data.type === "xml" && (
        <pre className="overflow-auto rounded-lg bg-slate-900 p-4 text-[12px] leading-relaxed text-emerald-200">{data.snippet}</pre>
      )}
      <a href={fileUrl(data.document.file_url)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-lg bg-[#1f3a5f] px-3 py-1.5 text-[13px] font-medium text-white hover:bg-[#16304f]">
        <ExternalLink className="h-3.5 w-3.5" /> {t("src.open")}
      </a>
    </div>
  );
}

function LineageRow({ left, right, doc, loc, onPick }: {
  left: React.ReactNode; right: React.ReactNode; doc: number | null; loc: string | null; onPick: (r: SourceRequest) => void;
}) {
  return (
    <button
      type="button"
      disabled={!doc}
      onClick={() => doc && onPick({ kind: "source", document_id: doc, locator: loc })}
      className="flex w-full items-center justify-between gap-3 rounded-md px-2 py-1.5 text-left text-[12.5px] hover:bg-slate-50 disabled:cursor-default"
    >
      <span className="min-w-0 truncate text-slate-600">{left}</span>
      <span className="flex items-center gap-2 tabular-nums text-slate-900">{right}<span className="text-[11px] text-slate-400">{loc}</span></span>
    </button>
  );
}

function ActivityView({ req, onPick }: { req: Extract<SourceRequest, { kind: "activity" }>; onPick: (r: SourceRequest) => void }) {
  const { t, lang, label } = useApp();
  const { data, error, loading } = useApi<ActivityLineage>(`/api/projects/${req.project}/lineage/${req.activity}`);
  if (loading && !data) return <Loading />;
  if (error) return <ErrorState message={error} />;
  if (!data) return null;
  const byPeriod = new Map<string, typeof data.costs>();
  data.costs.forEach((c) => byPeriod.set(c.period, [...(byPeriod.get(c.period) ?? []), c]));
  return (
    <div className="space-y-5">
      <div>
        <p className="text-[12px] font-medium uppercase tracking-wide text-slate-400">{t("src.lineage")} · {data.project}</p>
        <p className="text-lg font-semibold text-slate-900">{label("activities", data.activity)}</p>
      </div>
      {data.progress && (
        <section>
          <h3 className="mb-1 text-[12px] font-semibold text-slate-500">{t("src.progress")}</h3>
          <LineageRow onPick={onPick} left={period(data.progress.period, lang)} right={pct(data.progress.pct, lang)} doc={data.progress.document_id} loc={data.progress.locator} />
        </section>
      )}
      <section>
        <h3 className="mb-1 text-[12px] font-semibold text-slate-500">{t("src.budget")}</h3>
        {data.budget.map((b, i) => (
          <LineageRow onPick={onPick} key={i} left={<>{label("cost_types", b.cost_type)} <Badge tone={b.origin === "original" ? "neutral" : "violet"} className="ml-1">{t(`src.origin.${b.origin}`)}{b.co_number ? ` ${b.co_number}` : ""}</Badge></>}
            right={money(b.amount, lang, data.currency, false)} doc={b.document_id} loc={b.locator} />
        ))}
      </section>
      <section>
        <h3 className="mb-1 text-[12px] font-semibold text-slate-500">{t("src.costs")}</h3>
        <div className="max-h-[40vh] overflow-auto">
          {[...byPeriod.entries()].map(([p, rows]) => (
            <div key={p} className="border-t border-slate-100 py-1 first:border-0">
              <p className="px-2 pt-1 text-[11px] font-semibold text-slate-400">{period(p, lang)}</p>
              {rows.map((c, i) => <LineageRow onPick={onPick} key={i} left={label("cost_types", c.cost_type)} right={money(c.amount, lang, data.currency, false)} doc={c.document_id} loc={c.locator} />)}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export default function SourceDrawer() {
  const { source } = useApp();
  if (!source) return null;
  // a new request remounts the drawer, which resets its navigation stack
  return <Drawer key={JSON.stringify(source)} initial={source} />;
}

function Drawer({ initial }: { initial: SourceRequest }) {
  const { closeSource, t } = useApp();
  const [stack, setStack] = useState<SourceRequest[]>([initial]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && closeSource();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [closeSource]);

  const current = stack[stack.length - 1];
  return (
    <div className="fixed inset-0 z-[60] flex justify-end">
      <div className="absolute inset-0 bg-slate-900/20" onClick={closeSource} />
      <aside className="relative flex h-full w-full max-w-[640px] flex-col bg-white shadow-2xl">
        <header className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <div className="flex items-center gap-2">
            {stack.length > 1 && (
              <button onClick={() => setStack((s) => s.slice(0, -1))} className="rounded p-1 text-slate-500 hover:bg-slate-100"><ArrowLeft className="h-4 w-4" /></button>
            )}
            <div>
              <p className="text-sm font-semibold text-slate-900">{t("src.title")}</p>
              <p className="text-[12px] text-slate-500">{t("src.explain")}</p>
            </div>
          </div>
          <button onClick={closeSource} className="rounded p-1 text-slate-500 hover:bg-slate-100" aria-label={t("common.close")}><X className="h-5 w-5" /></button>
        </header>
        <div className="flex-1 overflow-y-auto p-5">
          {current.kind === "source"
            ? <PreviewView key={`${current.document_id}-${current.locator}`} req={current} />
            : <ActivityView req={current} onPick={(r) => setStack((s) => [...s, r])} />}
        </div>
      </aside>
    </div>
  );
}
