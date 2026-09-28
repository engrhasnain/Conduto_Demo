"use client";

import clsx from "clsx";
import {
  ArrowRight, BarChart3, CheckCircle2, ChevronRight, FolderOpen, GanttChart, Handshake, Landmark, Loader2, Mail, Plug, RefreshCw,
  ShieldCheck, Smartphone, TriangleAlert, Zap,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { useApp } from "@/components/providers";
import { Badge, Card, DetailDrawer, ErrorState, Loading, PageHeader, Select, SourceLink, Stat, Td, Th, type Tone } from "@/components/ui";
import { api, type Connector, type ConnectorsResp, type ConnectorStatus, type SyncRun } from "@/lib/api";
import { ago, money, num } from "@/lib/format";
import { invalidateAll, useApi } from "@/lib/useApi";

const ICON: Record<Connector["category"], typeof Plug> = {
  files: FolderOpen, accounting: Landmark, sales: Handshake, schedules: GanttChart, email: Mail, reporting: BarChart3, field: Smartphone,
};
const STATUS_TONE: Record<ConnectorStatus, Tone> = { connected: "green", available: "blue", planned: "neutral" };
const RUN_TONE: Record<SyncRun["status"], Tone> = { ok: "green", attention: "amber", error: "red" };
const CATEGORIES: Connector["category"][] = ["files", "accounting", "sales", "schedules", "email", "reporting", "field"];

function useEvery() {
  const { t } = useApp();
  return (m: number) => (m >= 1440 ? t("con.every_day") : m >= 60 ? t("con.every_hour") : t("con.every_min", { n: m }));
}

function StatusBadge({ status }: { status: ConnectorStatus }) {
  const { t } = useApp();
  return (
    <Badge tone={STATUS_TONE[status]}>
      {status === "connected" ? <CheckCircle2 className="h-3 w-3" /> : status === "available" ? <Plug className="h-3 w-3" /> : null}
      {t(`con.status.${status}`)}
    </Badge>
  );
}

/** One line saying what the last run found, in plain words. */
function RunSummary({ c, run }: { c: Pick<Connector, "key">; run: SyncRun }) {
  const { t, lang } = useApp();
  if (c.key === "files" && run.issues) return <>{t("con.run.files_waiting", { n: run.issues })}</>;
  if (c.key === "dynamics_gp" && run.issues) return <>{t("con.run.gp_diffs", { n: run.issues })}</>;
  if (run.new || run.updated) return <>{t("con.run.changes", { n: run.new, u: run.updated })}</>;
  return <>{t("con.run.read", { n: num(run.read, lang) })}</>;
}

function ConnectorCard({ c, onOpen }: { c: Connector; onOpen: () => void }) {
  const { t, lang } = useApp();
  const Icon = ICON[c.category];
  const every = useEvery();
  const run = c.last_run;
  return (
    <button onClick={onOpen}
      className={clsx("group flex flex-col rounded-xl bg-white p-4 text-left ring-1 ring-black/[0.07] transition-shadow hover:shadow-md hover:ring-[#2a78d6]/40",
        c.status === "planned" && "bg-slate-50/60")}>
      <div className="flex items-start gap-3">
        <div className={clsx("rounded-lg p-2", c.status === "connected" ? "bg-blue-50 text-[#1c5cab]" : "bg-slate-100 text-slate-500")}><Icon className="h-5 w-5" /></div>
        <div className="min-w-0 flex-1">
          <p className="text-[14.5px] font-semibold text-slate-900">{c.name[lang]}</p>
          <p className="text-[12px] text-slate-500">{t(`con.cat.${c.category}`)} · {c.direction === "in" ? t("con.dir.in") : t("con.dir.out")}</p>
        </div>
        <StatusBadge status={c.status} />
      </div>
      <p className="mt-3 line-clamp-3 flex-1 text-[12.5px] leading-relaxed text-slate-600">{c.summary[lang]}</p>
      <div className="mt-3 border-t border-slate-100 pt-2.5 text-[12px]">
        {c.status === "connected" && run ? (
          <div className="space-y-1">
            <p className="flex items-center gap-1.5 text-slate-500"><RefreshCw className="h-3 w-3" /> {t("con.last", { when: ago(run.at, lang) })} · {every(c.every_minutes)}</p>
            <p className={clsx("flex items-center gap-1.5 font-medium", run.issues ? "text-amber-700" : "text-emerald-700")}>
              {run.issues ? <TriangleAlert className="h-3.5 w-3.5" /> : <CheckCircle2 className="h-3.5 w-3.5" />} <RunSummary c={c} run={run} />
            </p>
          </div>
        ) : (
          <p className="text-slate-500">{t(`con.phase.${c.phase}`)}</p>
        )}
        <p className="mt-1.5 flex items-center gap-0.5 font-medium text-[#2a78d6] opacity-70 group-hover:opacity-100">{t("common.details")} <ChevronRight className="h-3 w-3" /></p>
      </div>
    </button>
  );
}

function ChangeList({ run }: { run: SyncRun }) {
  const { t, lang } = useApp();
  const changes = run.details.changes ?? [];
  const fmt = (field: string, v: unknown, currency?: string) =>
    field === "stage" ? t(`bid.stage.${v}`) : field === "value" ? money(v as number, lang, currency ?? "USD", false) : field === "probability" || field === "bid_margin_pct" ? `${Math.round((v as number) * 100)}%` : String(v ?? "–");
  if (!changes.length) return null;
  return (
    <ul className="mt-2 space-y-1.5">
      {changes.map((ch) => (
        <li key={ch.crm_id} className="rounded-lg bg-white px-3 py-2 text-[12.5px] ring-1 ring-slate-200">
          <p className="font-medium text-slate-900">
            <Badge tone={ch.kind === "new" ? "violet" : "blue"} className="mr-1.5">{t(`con.change.${ch.kind}`)}</Badge>
            {ch.crm_id} · {ch.name}
          </p>
          {ch.fields?.map((f) => (
            <p key={f.field} className="mt-0.5 text-slate-600">{t(`con.field.${f.field}`)}: <span className="text-slate-400">{fmt(f.field, f.old, ch.currency)}</span> → <b>{fmt(f.field, f.new, ch.currency)}</b></p>
          ))}
        </li>
      ))}
    </ul>
  );
}

function ConnectorDetail({ id }: { id: string }) {
  const { t, lang } = useApp();
  const { data: c, error } = useApi<Connector>(`/api/connectors/${id}`);
  const [busy, setBusy] = useState<null | "sync" | "test">(null);
  const [result, setResult] = useState<null | { kind: "sync"; run: SyncRun } | { kind: "test"; ms: number; details: Record<string, number | string> }>(null);
  const [err, setErr] = useState<string | null>(null);
  const every = useEvery();

  async function doSync() {
    setBusy("sync");
    setErr(null);
    setResult(null);
    try {
      const [run] = await Promise.all([api<SyncRun>(`/api/connectors/${id}/sync`, { method: "POST" }), new Promise((r) => setTimeout(r, 900))]);
      setResult({ kind: "sync", run });
      invalidateAll();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(null);
    }
  }
  async function doTest() {
    setBusy("test");
    setErr(null);
    setResult(null);
    try {
      const [r] = await Promise.all([api<{ ms: number; details: Record<string, number | string> }>(`/api/connectors/${id}/test`, { method: "POST" }), new Promise((res) => setTimeout(res, 600))]);
      setResult({ kind: "test", ...r });
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  if (error) return <ErrorState message={error} />;
  if (!c) return <Loading />;
  const connected = c.status === "connected";
  return (
    <div className="space-y-5 text-[13px]">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={c.status} />
        <Badge>{c.direction === "in" ? t("con.dir.in") : t("con.dir.out")}</Badge>
        <Badge><ShieldCheck className="h-3 w-3" /> {t("con.readonly")}</Badge>
        {connected ? <Badge>{every(c.every_minutes)}</Badge> : <Badge tone="violet">{t(`con.phase.${c.phase}`)}</Badge>}
      </div>

      {connected && (
        <div className="rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200">
          <div className="flex flex-wrap items-center gap-2">
            <button onClick={doSync} disabled={!!busy}
              className="inline-flex items-center gap-2 rounded-lg bg-[#132a45] px-3.5 py-2 text-[13px] font-medium text-white disabled:opacity-50">
              {busy === "sync" ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />} {busy === "sync" ? t("con.syncing") : t("con.sync")}
            </button>
            <button onClick={doTest} disabled={!!busy}
              className="inline-flex items-center gap-2 rounded-lg bg-white px-3.5 py-2 text-[13px] font-medium text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50 disabled:opacity-50">
              {busy === "test" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />} {t("con.test")}
            </button>
            <span className="text-[12px] text-slate-500">{t("con.records", { n: num(c.records, lang) })}</span>
          </div>
          {err && <p className="mt-3 text-[12.5px] text-red-700">{err === "network" ? t("shell.api_down") : err}</p>}
          {result?.kind === "test" && (
            <p className="mt-3 flex items-center gap-2 text-[13px] text-emerald-800"><CheckCircle2 className="h-4 w-4 text-[#0ca30c]" /> {t(`con.test_ok.${c.key}`, { ...result.details, ms: result.ms })}</p>
          )}
          {result?.kind === "sync" && (
            <div className="mt-3">
              <p className={clsx("flex items-center gap-2 font-medium", result.run.issues ? "text-amber-800" : "text-emerald-800")}>
                {result.run.issues ? <TriangleAlert className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4 text-[#0ca30c]" />}
                {t("con.result", { read: num(result.run.read, lang), n: result.run.new, u: result.run.updated })}
              </p>
              {c.key === "files" && !!result.run.details.waiting?.length && (
                <p className="mt-1 text-slate-600">{t("con.run.files_waiting", { n: result.run.details.waiting.length })}: {result.run.details.waiting.join(", ")}.{" "}
                  <Link href="/ingest" className="font-medium text-[#2a78d6] hover:underline">{t("con.go.ingest")}</Link></p>
              )}
              {c.key === "dynamics_gp" && (
                <p className="mt-1 text-slate-600">{t("con.gp_result", { matched: result.run.details.matched ?? 0, cells: result.run.details.cells ?? 0, d: result.run.details.differences ?? 0 })}{" "}
                  <Link href="/data" className="font-medium text-[#2a78d6] hover:underline">{t("con.go.data")}</Link></p>
              )}
              {c.key === "sales" && (
                <>
                  {!result.run.new && !result.run.updated && <p className="mt-1 text-slate-600">{t("con.no_changes")}</p>}
                  <ChangeList run={result.run} />
                  <Link href="/bids" className="mt-2 inline-flex items-center gap-1 font-medium text-[#2a78d6] hover:underline">{t("con.go.bids")} <ArrowRight className="h-3.5 w-3.5" /></Link>
                </>
              )}
            </div>
          )}
        </div>
      )}

      <p className="leading-relaxed text-slate-700">{c.summary[lang]}</p>
      {c.note && <p className="rounded-lg bg-amber-50 p-3 text-[12.5px] leading-relaxed text-amber-900 ring-1 ring-amber-200">{c.note[lang]}</p>}

      <section>
        <p className="mb-1.5 font-semibold text-slate-900">{c.direction === "in" ? t("con.d.reads") : t("con.d.sends")}</p>
        <ul className="list-disc space-y-0.5 pl-5 text-slate-700">{c.reads.map((r, i) => <li key={i}>{r[lang]}</li>)}</ul>
      </section>
      <section>
        <p className="mb-1.5 font-semibold text-slate-900">{t("con.d.how")}</p>
        <p className="leading-relaxed text-slate-700">{c.method[lang]}</p>
      </section>
      <section>
        <p className="mb-1.5 font-semibold text-slate-900">{t("con.d.mapping")}</p>
        <p className="mb-2 text-[12px] text-slate-500">{t("con.d.mapping_sub")}</p>
        <div className="divide-y divide-slate-100 rounded-lg ring-1 ring-slate-200">
          {c.mapping.map((m, i) => (
            <div key={i} className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 px-3 py-2">
              <span className="text-slate-700">{m.source[lang]}</span>
              <ArrowRight className="h-3.5 w-3.5 text-slate-400" />
              <span className="font-medium text-slate-900">{m.target[lang]}</span>
            </div>
          ))}
        </div>
      </section>
      <section>
        <p className="mb-1.5 font-semibold text-slate-900">{connected ? t("con.d.setup_done") : t("con.d.setup")}</p>
        <ul className="space-y-1">
          {c.setup.map((s, i) => (
            <li key={i} className="flex items-start gap-2 text-slate-700">
              {connected ? <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#0ca30c]" /> : <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-400" />}
              {s[lang]}
            </li>
          ))}
        </ul>
      </section>

      {connected && !!c.runs?.length && (
        <section>
          <p className="mb-1.5 font-semibold text-slate-900">{t("con.d.history")}</p>
          <div className="overflow-x-auto rounded-lg ring-1 ring-slate-200">
            <table className="min-w-full text-[12.5px]">
              <thead className="border-b border-slate-200 bg-slate-50/60">
                <tr><Th>{t("con.h.when")}</Th><Th>{t("con.h.how")}</Th><Th right>{t("con.h.read")}</Th><Th right>{t("con.h.new")}</Th><Th right>{t("con.h.updated")}</Th><Th>{t("con.h.result")}</Th><Th /></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {c.runs.map((r) => (
                  <tr key={r.id}>
                    <Td className="whitespace-nowrap text-slate-600" >{ago(r.at, lang)}</Td>
                    <Td className="whitespace-nowrap">{t(`con.trigger.${r.trigger}`)}</Td>
                    <Td right>{num(r.read, lang)}</Td>
                    <Td right>{r.new || "–"}</Td>
                    <Td right>{r.updated || "–"}</Td>
                    <Td><Badge tone={RUN_TONE[r.status]}>{r.issues ? <RunSummary c={c} run={r} /> : t(`con.run.${r.status}`)}</Badge></Td>
                    <Td>{r.document_id && <SourceLink document_id={r.document_id} locator={null}>{t("con.snapshot")}</SourceLink>}</Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

export default function ConnectorsPage() {
  const { t, lang } = useApp();
  const { data, error, loading, reload } = useApi<ConnectorsResp>("/api/connectors");
  const [status, setStatus] = useState<"all" | ConnectorStatus>("all");
  const [cat, setCat] = useState<"all" | Connector["category"]>("all");
  const [open, setOpen] = useState<string | null>(null);

  const shown = useMemo(
    () => (data?.connectors ?? []).filter((c) => (status === "all" || c.status === status) && (cat === "all" || c.category === cat)),
    [data, status, cat],
  );
  if (error && !data) return <ErrorState message={error} onRetry={reload} />;
  if (loading || !data) return <Loading />;
  const s = data.summary;
  const openConnector = data.connectors.find((c) => c.key === open);
  const firstAttention = data.connectors.find((c) => c.last_run?.issues);
  const groups: ConnectorStatus[] = ["connected", "available", "planned"];

  return (
    <div className="space-y-6">
      <PageHeader title={t("con.title")} subtitle={t("con.sub")}>
        <div className="flex flex-wrap items-center gap-2">
          <Select label={t("con.f.status")} value={status} onChange={setStatus} options={[
            { value: "all", label: t("common.all") }, ...groups.map((g) => ({ value: g, label: t(`con.status.${g}`) }))]} />
          <Select label={t("con.f.category")} value={cat} onChange={setCat} options={[
            { value: "all", label: t("common.all") }, ...CATEGORIES.map((k) => ({ value: k, label: t(`con.cat.${k}`) }))]} />
        </div>
      </PageHeader>

      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#0f2440] via-[#132a45] to-[#1c5cab] p-6 text-white shadow-lg">
        <p className="text-[12px] font-semibold uppercase tracking-[0.18em] text-sky-300">{t("con.hero")}</p>
        <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr] md:items-center">
          {(["con.flow.1", "con.flow.2", "con.flow.3", "con.flow.4"] as const).map((k, i) => (
            <div key={k} className="contents">
              <div className="rounded-xl bg-white/10 p-3.5">
                <p className="text-[13.5px] font-semibold">{t(`${k}.title`)}</p>
                <p className="mt-0.5 text-[12px] leading-snug text-sky-100/80">{t(`${k}.body`)}</p>
              </div>
              {i < 3 && <ArrowRight className="hidden h-4 w-4 text-sky-300/70 md:block" />}
            </div>
          ))}
        </div>
        <p className="mt-4 flex items-start gap-2 text-[13px] text-sky-100"><Landmark className="mt-0.5 h-4 w-4 shrink-0 text-sky-300" /> {t("con.erp_message")}</p>
      </section>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label={t("con.kpi.connected")} value={s.connected} sub={t("con.kpi.connected_sub")} onClick={() => setStatus("connected")} />
        <Stat label={t("con.kpi.records")} value={num(s.records, lang)} sub={t("con.kpi.records_sub")} onClick={() => setStatus("connected")} />
        <Stat label={t("con.kpi.attention")} value={s.attention} tone={s.attention ? "amber" : undefined}
          sub={t("con.kpi.attention_sub", { files: s.waiting_files, diffs: s.attention - s.waiting_files })} onClick={firstAttention ? () => setOpen(firstAttention.key) : undefined} />
        <Stat label={t("con.kpi.next")} value={s.available + s.planned} sub={t("con.kpi.next_sub", { a: s.available, p: s.planned })} onClick={() => setStatus("available")} />
      </div>

      {groups.map((g) => {
        const items = shown.filter((c) => c.status === g);
        if (!items.length) return null;
        return (
          <section key={g}>
            <div className="mb-3 flex items-baseline gap-2">
              <h2 className="text-[15px] font-semibold text-slate-900">{t(`con.group.${g}`)}</h2>
              <span className="text-[12.5px] text-slate-500">{t(`con.group.${g}_sub`)}</span>
            </div>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {items.map((c) => <ConnectorCard key={c.key} c={c} onOpen={() => setOpen(c.key)} />)}
            </div>
          </section>
        );
      })}
      {!shown.length && <Card><p className="py-6 text-center text-[13px] text-slate-400">{t("con.empty")}</p></Card>}

      <DetailDrawer open={!!openConnector} onClose={() => setOpen(null)} title={openConnector ? openConnector.name[lang] : ""}
        explain={openConnector ? t(`con.cat.${openConnector.category}`) : undefined}>
        {open && <ConnectorDetail key={open} id={open} />}
      </DetailDrawer>
      <p className="text-[12px] text-slate-400">{t("con.demo_note")}</p>
    </div>
  );
}
