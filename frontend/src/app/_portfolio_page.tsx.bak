"use client";

import clsx from "clsx";
import { AlertOctagon, ArrowRight, Download, FileWarning, Mountain, ShieldCheck, SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import Chart, { ChartOption } from "@/components/Chart";
import { useChat } from "@/components/chat/ChatProvider";
import { useApp } from "@/components/providers";
import { Card, DetailDrawer, ErrorState, Flags, HealthBadge, Loading, PageHeader, ProgressBar, Select, SourceLink, Stat, Td, Th } from "@/components/ui";
import { API_URL, type Datahub, type Insight, type Portfolio, type ProjectRow } from "@/lib/api";
import { axisBase, C, legendBase, tooltipBase } from "@/lib/chartTheme";
import { money, num, pct, period, pts, ratio } from "@/lib/format";
import { useApi } from "@/lib/useApi";

function InsightCard({ ins }: { ins: Insight }) {
  const { t, lang } = useApp();
  const { openWith } = useChat();
  const p = ins.params as Record<string, number>;
  let icon = <AlertOctagon className="h-4 w-4 text-red-600" />;
  let title = "", body = "", cta = "", href = "/";
  let accent = "border-l-red-500";
  if (ins.code === "worst_project") {
    title = t("pf.ins.worst.title", { code: ins.project ?? "", erosion: pts(p.erosion, lang, false) });
    body = t("pf.ins.worst.body", { bid: pct(p.bid, lang), forecast: pct(p.forecast, lang), pending: money(p.pending_usd, lang), recover: pts(p.recover_pts, lang) });
    cta = t("pf.ins.worst.cta");
    href = `/projects/${ins.project}`;
  } else if (ins.code === "pending_cos") {
    icon = <FileWarning className="h-4 w-4 text-violet-600" />;
    accent = "border-l-violet-500";
    title = t("pf.ins.pending.title", { total: money(p.total_usd, lang) });
    body = t("pf.ins.pending.body", { count: p.count, aged_count: p.aged_count, aged: money(p.aged_usd, lang) });
    cta = t("pf.ins.pending.cta");
    href = "#ask";
  } else {
    icon = <Mountain className="h-4 w-4 text-[#1baf7a]" />;
    accent = "border-l-[#1baf7a]";
    title = t("pf.ins.terrain.title");
    body = t("pf.ins.terrain.body", { n: p.n, rf: pts(-p.rainforest, lang), coast: pts(-p.coast, lang) });
    cta = t("pf.ins.terrain.cta");
    href = "/benchmarks";
  }
  return (
    <div className={clsx("flex flex-col rounded-xl border-l-4 bg-white p-4 ring-1 ring-black/[0.07]", accent)}>
      <div className="flex items-start gap-2">
        <span className="mt-0.5">{icon}</span>
        <p className="text-[14px] font-semibold leading-snug text-slate-900">{title}</p>
      </div>
      <p className="mt-2 flex-1 text-[13px] leading-relaxed text-slate-600">{body}</p>
      {href === "#ask" ? (
        <button onClick={() => openWith(t("chat.pending_q"))} className="mt-3 inline-flex items-center gap-1 self-start text-[13px] font-medium text-[#2a78d6] hover:underline">
          {cta} <ArrowRight className="h-3.5 w-3.5" />
        </button>
      ) : (
        <Link href={href} className="mt-3 inline-flex items-center gap-1 text-[13px] font-medium text-[#2a78d6] hover:underline">
          {cta} <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      )}
    </div>
  );
}

type Filters = { country: "all" | "EC" | "PE" | "BR"; status: "active" | "closed" | "all"; health: "all" | "red" | "amber" | "green"; terrain: "all" | "coast" | "highlands" | "rainforest"; q: string };
const NO_FILTERS: Filters = { country: "all", status: "active", health: "all", terrain: "all", q: "" };
type Detail = null | "projects" | "contract" | "margin" | "pending";

interface PendingCo {
  project: string; project_name: string; number: string; titles: Record<string, string>; amount_usd: number; days_pending: number | null;
  document_id: number | null; locator: string | null; cause: string;
}

export default function PortfolioPage() {
  const { t, lang, country, label } = useApp();
  const router = useRouter();
  const { data, error, loading, reload } = useApi<Portfolio>("/api/portfolio");
  const { data: hub } = useApi<Datahub>("/api/datahub");
  const [f, setF] = useState<Filters>(NO_FILTERS);
  const [detail, setDetail] = useState<Detail>(null);
  const { data: allPending } = useApi<PendingCo[]>(detail === "pending" ? "/api/change_orders?status=pending" : null);
  const set = <K extends keyof Filters>(k: K, v: Filters[K]) => setF((x) => ({ ...x, [k]: v }));
  const filtered = f !== NO_FILTERS && JSON.stringify(f) !== JSON.stringify(NO_FILTERS);

  // everything on the page follows the filters
  const rows = useMemo(() => {
    const nq = f.q.trim().toLowerCase();
    return (data?.projects ?? [])
      .filter((p) => f.status === "all" || p.status === f.status)
      .filter((p) => f.country === "all" || p.country === f.country)
      .filter((p) => f.terrain === "all" || p.terrain === f.terrain)
      .filter((p) => f.health === "all" || p.health === f.health)
      .filter((p) => !nq || `${p.code} ${p.name} ${p.client}`.toLowerCase().includes(nq))
      .sort((a, b) => (a.status === b.status ? b.margin_erosion_pts - a.margin_erosion_pts : a.status === "active" ? -1 : 1));
  }, [data, f]);
  const active = useMemo(() => rows.filter((p) => p.status === "active"), [rows]);
  const scope = f.status === "closed" ? rows : active; // money figures describe active work unless looking at closed projects
  const pendingCos = useMemo(() => {
    const codes = new Set(rows.map((p) => p.code));
    return allPending?.filter((c) => codes.has(c.project)) ?? null;
  }, [allPending, rows]);

  const kpi = useMemo(() => {
    const revised = scope.reduce((a, p) => a + p.revised_contract_usd, 0);
    return {
      n: scope.length,
      closed: (data?.projects ?? []).filter((p) => p.status === "closed" && (f.country === "all" || p.country === f.country)
        && (f.terrain === "all" || p.terrain === f.terrain) && (!f.q.trim() || `${p.code} ${p.name} ${p.client}`.toLowerCase().includes(f.q.trim().toLowerCase()))).length,
      contract: scope.reduce((a, p) => a + p.contract_value_usd, 0),
      eac: scope.reduce((a, p) => a + p.eac_usd, 0),
      margin: revised ? scope.reduce((a, p) => a + p.forecast_margin_usd, 0) / revised : null,
      bid: scope.length ? scope.reduce((a, p) => a + p.bid_margin_pct * p.contract_value_usd, 0) / Math.max(scope.reduce((a, p) => a + p.contract_value_usd, 0), 1) : null,
      pending: rows.reduce((a, p) => a + p.pending_co_usd, 0),
      pendingN: rows.reduce((a, p) => a + p.pending_co_count, 0),
      health: { red: active.filter((p) => p.health === "red").length, amber: active.filter((p) => p.health === "amber").length, green: active.filter((p) => p.health === "green").length },
    };
  }, [scope, rows, active, data, f]);

  const marginRows = useMemo(() => [...scope].sort((a, b) => a.margin_erosion_pts - b.margin_erosion_pts), [scope]);
  const marginOption = useMemo<ChartOption>(() => ({
    grid: { left: 70, right: 56, top: 30, bottom: 24 },
    legend: { ...legendBase, data: [t("pf.chart.bid"), t("pf.chart.forecast")] },
    tooltip: {
      ...tooltipBase, trigger: "axis", axisPointer: { type: "shadow", shadowStyle: { color: "rgba(0,0,0,0.03)" } },
      formatter: (ps: { dataIndex: number }[]) => {
        const r = marginRows[ps[0].dataIndex];
        return `<b>${r.code}</b> ${r.name}<br/>${t("pf.chart.bid")}: ${pct(r.bid_margin_pct, lang)}<br/>${t("pf.chart.forecast")}: <b>${pct(r.forecast_margin_pct, lang)}</b> (${pts(-r.margin_erosion_pts, lang)})`;
      },
    },
    xAxis: { type: "value", ...axisBase, axisLabel: { ...axisBase.axisLabel, formatter: (v: number) => pct(v, lang, 0) } },
    yAxis: { type: "category", data: marginRows.map((r) => r.code), ...axisBase, axisLabel: { color: C.ink2, fontSize: 12 }, splitLine: { show: false } },
    series: [
      { name: t("pf.chart.bid"), type: "bar", data: marginRows.map((r) => r.bid_margin_pct), barWidth: 8, barGap: "30%", itemStyle: { color: C.bidGray, borderRadius: [0, 4, 4, 0] } },
      {
        name: t("pf.chart.forecast"), type: "bar", data: marginRows.map((r) => r.forecast_margin_pct), barWidth: 8,
        itemStyle: { color: C.s1, borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: "right", color: C.ink2, fontSize: 11, formatter: (p: { value: number }) => pct(p.value, lang) },
      },
    ],
  }), [marginRows, lang, t]);

  const byCountry = useMemo(() => (["EC", "PE", "BR"] as const).map((c) => {
    const items = scope.filter((p) => p.country === c);
    const rev = items.reduce((a, p) => a + p.revised_contract_usd, 0);
    return { country: c, n: items.length, contract: items.reduce((a, p) => a + p.contract_value_usd, 0), margin: rev ? items.reduce((a, p) => a + p.forecast_margin_usd, 0) / rev : null };
  }).filter((r) => r.n > 0), [scope]);
  const countryOption = useMemo<ChartOption>(() => ({
    grid: { left: 60, right: 16, top: 24, bottom: 28 },
    tooltip: {
      ...tooltipBase, trigger: "item",
      formatter: (p: { dataIndex: number }) => {
        const r = byCountry[p.dataIndex];
        return `<b>${country(r.country)}</b><br/>${money(r.contract, lang)} · ${r.n}<br/>${t("pf.kpi.margin")}: ${pct(r.margin, lang)}`;
      },
    },
    xAxis: { type: "category", data: byCountry.map((r) => country(r.country)), ...axisBase, splitLine: { show: false }, axisLabel: { color: C.ink2, fontSize: 12 } },
    yAxis: { type: "value", ...axisBase, axisLabel: { ...axisBase.axisLabel, formatter: (v: number) => money(v, lang).replace("USD ", "") } },
    series: [{
      type: "bar", data: byCountry.map((r) => r.contract), barWidth: 28, itemStyle: { color: C.s1, borderRadius: [4, 4, 0, 0] }, cursor: "pointer",
      label: { show: true, position: "top", color: C.ink2, fontSize: 11, formatter: (p: { value: number }) => money(p.value, lang) },
    }],
  }), [byCountry, lang, country, t]);

  if (error && !data) return <ErrorState message={error} onRetry={reload} />;
  if (loading || !data) return <Loading />;

  const scrollToTable = () => document.getElementById("projects")?.scrollIntoView({ behavior: "smooth", block: "start" });
  const go = (code: string) => router.push(`/projects/${code}`);
  const projectLink = (p: ProjectRow) => (
    <button onClick={() => go(p.code)} className="text-left"><span className="font-semibold text-[#2a78d6] hover:underline">{p.code}</span> <span className="text-slate-600">{p.name}</span></button>
  );

  return (
    <>
      <PageHeader title={t("pf.title")} subtitle={t("pf.subtitle", { n: data.projects.length, period: period(data.status_period, lang, true) })}>
        <a href={`${API_URL}/api/export/consolidated.xlsx?lang=${lang}`} className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-[13px] font-medium text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50">
          <Download className="h-3.5 w-3.5" /> {t("dh.export")}
        </a>
      </PageHeader>

      {hub && (
        <Link href="/data" className="mb-6 flex flex-wrap items-center gap-3 rounded-xl bg-gradient-to-r from-[#132a45] to-[#1c5cab] px-5 py-3 text-[13.5px] text-white shadow-sm hover:opacity-95">
          <ShieldCheck className="h-4 w-4 text-sky-300" />
          <span className="flex-1">{t("pf.strip", {
            files: hub.files.total, records: num(hub.records_total, lang),
            findings: hub.quality.erp_vs_excel.discrepancies.length + hub.quality.report_vs_workbook.mismatches.length + hub.anomalies.unexplained,
          })}</span>
          <span className="inline-flex items-center gap-1 font-semibold">{t("pf.strip_cta")} <ArrowRight className="h-3.5 w-3.5" /></span>
        </Link>
      )}

      <p className="mb-2 text-[12px] font-semibold uppercase tracking-wide text-slate-400">{t("pf.highlights")}</p>
      <div className="mb-6 grid gap-4 md:grid-cols-3">
        {data.insights.map((ins) => <InsightCard key={ins.code} ins={ins} />)}
      </div>

      <div className="sticky top-[53px] z-20 -mx-4 mb-5 flex flex-wrap items-center gap-2 border-y border-slate-200 bg-[#f5f6f8]/95 px-4 py-2.5 backdrop-blur lg:-mx-8 lg:px-8">
        <p className="mr-1 flex items-center gap-1.5 text-[13px] font-semibold text-slate-700"><SlidersHorizontal className="h-4 w-4" /> {t("pf.filters")}</p>
        <Select label={t("pf.f.status")} value={f.status} onChange={(v) => set("status", v)} options={[
          { value: "active", label: t("common.active") }, { value: "closed", label: t("common.closed") }, { value: "all", label: t("common.all") }]} />
        <Select label={t("pf.f.country")} value={f.country} onChange={(v) => set("country", v)} options={[
          { value: "all", label: t("common.all") }, { value: "EC", label: country("EC") }, { value: "PE", label: country("PE") }, { value: "BR", label: country("BR") }]} />
        <Select label={t("pf.f.terrain")} value={f.terrain} onChange={(v) => set("terrain", v)} options={[
          { value: "all", label: t("common.all") }, { value: "coast", label: label("terrains", "coast") }, { value: "highlands", label: label("terrains", "highlands") }, { value: "rainforest", label: label("terrains", "rainforest") }]} />
        <Select label={t("pf.f.health")} value={f.health} onChange={(v) => set("health", v)} options={[
          { value: "all", label: t("common.all") }, { value: "red", label: t("health.red") }, { value: "amber", label: t("health.amber") }, { value: "green", label: t("health.green") }]} />
        <input value={f.q} onChange={(e) => set("q", e.target.value)} placeholder={t("common.search")}
          className="h-8 w-48 rounded-lg border border-slate-200 bg-white px-2.5 text-[13px] outline-none focus:border-[#2a78d6]" />
        {filtered && <button onClick={() => setF(NO_FILTERS)} className="text-[12.5px] font-medium text-[#2a78d6] hover:underline">{t("pf.clear")}</button>}
        <span className="ml-auto text-[12.5px] text-slate-500">{t("pf.showing", { n: rows.length, total: data.projects.length })}</span>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-5">
        <Stat label={f.status === "closed" ? t("pf.kpi.closed") : t("pf.kpi.active")} value={kpi.n} onClick={() => setDetail("projects")}
          sub={f.status === "closed" ? undefined : t("pf.kpi.active_sub", { n: kpi.closed })} />
        <Stat label={t("pf.kpi.contract")} value={money(kpi.contract, lang)} onClick={() => setDetail("contract")} sub={t("pf.kpi.contract_sub", { eac: money(kpi.eac, lang) })} />
        <Stat label={t("pf.kpi.margin")} value={pct(kpi.margin, lang)} onClick={() => setDetail("margin")}
          tone={(kpi.bid ?? 0) - (kpi.margin ?? 0) > 0.03 ? "red" : undefined} sub={t("pf.kpi.margin_sub", { bid: pct(kpi.bid, lang) })} />
        <Stat label={t("pf.kpi.pending")} value={money(kpi.pending, lang)} onClick={() => setDetail("pending")} sub={t(kpi.pendingN === 1 ? "pf.kpi.pending_sub1" : "pf.kpi.pending_sub", { n: kpi.pendingN })} />
        <div className="col-span-2 rounded-xl bg-white p-4 ring-1 ring-black/[0.07] lg:col-span-1">
          <p className="text-[12px] font-medium text-slate-500">{t("pf.kpi.health")}</p>
          <div className="mt-2 space-y-1">
            {(["red", "amber", "green"] as const).map((h) => (
              <button key={h} onClick={() => { setF((x) => ({ ...x, health: h, status: "active" })); scrollToTable(); }}
                className={clsx("flex w-full items-center justify-between rounded-md px-1 py-0.5 hover:bg-slate-50", f.health === h && "bg-blue-50")}>
                <HealthBadge health={h} />
                <span className="text-[15px] font-semibold text-slate-900">{kpi.health[h]}</span>
              </button>
            ))}
          </div>
          <p className="mt-1 text-[11.5px] text-slate-400">{t("pf.health_hint")}</p>
        </div>
      </div>

      <div className="mb-6 grid gap-4 lg:grid-cols-3">
        <Card title={f.status === "closed" ? t("pf.chart.margin_closed") : t("pf.chart.margin")} subtitle={t("pf.chart.click")} className="lg:col-span-2">
          {marginRows.length ? (
            <Chart option={marginOption} height={Math.max(220, marginRows.length * 44 + 60)} onClick={(p) => go(marginRows[p.dataIndex].code)} ariaLabel={t("pf.chart.margin")} />
          ) : <p className="py-10 text-center text-sm text-slate-400">{t("pf.empty")}</p>}
        </Card>
        <Card title={t("pf.chart.country")} subtitle={t("pf.chart.click_country")}>
          {byCountry.length ? (
            <Chart option={countryOption} height={Math.max(220, marginRows.length * 44 + 60)} onClick={(p) => set("country", byCountry[p.dataIndex].country)} ariaLabel={t("pf.chart.country")} />
          ) : <p className="py-10 text-center text-sm text-slate-400">{t("pf.empty")}</p>}
        </Card>
      </div>

      <Card id="projects" title={`${t("pf.table.title")} (${rows.length})`} bodyClass="px-0 pb-2">
        <div className="overflow-x-auto">
          <table className="min-w-full text-[13px]">
            <thead className="border-y border-slate-100 bg-slate-50/60">
              <tr>
                <Th>{t("pf.col.project")}</Th>
                <Th wrap>{t("pf.col.progress")}</Th>
                <Th right wrap><span title={t("pf.cpi_help")} className="cursor-help underline decoration-dotted underline-offset-2">{t("pf.col.cpi")}</span></Th>
                <Th right wrap><span title={t("pf.spi_help")} className="cursor-help underline decoration-dotted underline-offset-2">{t("pf.col.spi")}</span></Th>
                <Th right>{t("pf.col.contract")}</Th>
                <Th wrap>{t("pf.col.margin")}</Th>
                <Th right wrap>{t("pf.col.pending")}</Th>
                <Th>{t("pf.col.flags")}</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((p: ProjectRow) => (
                <tr key={p.code} onClick={() => go(p.code)} className="cursor-pointer hover:bg-slate-50">
                  <Td className="min-w-[230px]">
                    <div className="flex items-center gap-2">
                      <HealthBadge health={p.health} />
                      <span className="font-semibold text-slate-900">{p.code}</span>
                      {p.origin === "upload" && <span className="text-[11px] text-violet-600">●</span>}
                    </div>
                    <p className="mt-0.5 text-slate-700">{p.name}</p>
                    <p className="text-[12px] text-slate-400">{country(p.country)} · {label("terrains", p.terrain)} · {p.kind === "pipeline" ? `${p.diameter_in}" × ${p.length_km} km` : t("kind.civil")}</p>
                  </Td>
                  <Td className="w-36">
                    {p.status === "active" ? (
                      <>
                        <ProgressBar actual={p.progress_pct} planned={p.planned_pct} />
                        <p className="mt-1 text-[12px] text-slate-500">{pct(p.progress_pct, lang, 0)} / {pct(p.planned_pct, lang, 0)}</p>
                      </>
                    ) : <span className="text-[12px] text-slate-400">{t("status.closed")} · {period(p.forecast_finish, lang)}</span>}
                  </Td>
                  <Td right className={clsx(p.cpi !== null && p.cpi < 0.95 && "font-semibold text-red-700")}>{ratio(p.cpi)}</Td>
                  <Td right className={clsx(p.spi !== null && p.spi < 0.92 && "font-semibold text-amber-700")}>{ratio(p.spi)}</Td>
                  <Td right>{money(p.contract_value_usd, lang)}</Td>
                  <Td className="whitespace-nowrap">
                    <span className="text-slate-400">{pct(p.bid_margin_pct, lang)}</span>
                    <span className="mx-1 text-slate-300">→</span>
                    <span className={clsx("font-semibold", p.margin_erosion_pts > 0.03 ? "text-red-700" : p.margin_erosion_pts < -0.005 ? "text-emerald-700" : "text-slate-900")}>{pct(p.forecast_margin_pct, lang)}</span>
                  </Td>
                  <Td right>{p.pending_co_count ? <span className="font-medium text-violet-700">{money(p.pending_co_usd, lang)}</span> : <span className="text-slate-300">—</span>}</Td>
                  <Td className="min-w-[170px]"><Flags flags={p.flags} max={2} /></Td>
                </tr>
              ))}
              {!rows.length && <tr><Td className="py-10 text-center text-slate-400">{t("pf.empty")}</Td></tr>}
            </tbody>
          </table>
        </div>
      </Card>

      <DetailDrawer open={detail === "projects"} onClose={() => setDetail(null)} title={`${f.status === "closed" ? t("pf.kpi.closed") : t("pf.kpi.active")} (${scope.length})`} explain={t("pf.d.projects")}>
        <table className="min-w-full text-[13px]">
          <thead className="border-b border-slate-200"><tr><Th>{t("pf.col.project")}</Th><Th>{t("pf.f.country")}</Th><Th right>{t("pj.k.progress")}</Th><Th>{t("pj.col.status")}</Th></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {scope.map((p) => (
              <tr key={p.code}><Td>{projectLink(p)}</Td><Td>{country(p.country)}</Td><Td right>{pct(p.progress_pct, lang, 0)}</Td><Td><HealthBadge health={p.health} /></Td></tr>
            ))}
          </tbody>
        </table>
      </DetailDrawer>

      <DetailDrawer open={detail === "contract"} onClose={() => setDetail(null)} title={t("pf.kpi.contract")} explain={t("pf.d.contract")}>
        <table className="min-w-full text-[13px]">
          <thead className="border-b border-slate-200"><tr><Th>{t("pf.col.project")}</Th><Th right>{t("pf.col.contract")}</Th><Th right>{t("pf.d.final_cost")}</Th><Th right>{t("pf.kpi.margin")}</Th></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {[...scope].sort((a, b) => b.contract_value_usd - a.contract_value_usd).map((p) => (
              <tr key={p.code}><Td>{projectLink(p)}</Td><Td right>{money(p.contract_value_usd, lang)}</Td><Td right>{money(p.eac_usd, lang)}</Td><Td right>{pct(p.forecast_margin_pct, lang)}</Td></tr>
            ))}
            <tr className="bg-slate-50 font-semibold"><Td>{t("pj.col.total")}</Td><Td right>{money(kpi.contract, lang)}</Td><Td right>{money(kpi.eac, lang)}</Td><Td right>{pct(kpi.margin, lang)}</Td></tr>
          </tbody>
        </table>
      </DetailDrawer>

      <DetailDrawer open={detail === "margin"} onClose={() => setDetail(null)} title={t("pf.kpi.margin")} explain={t("pf.d.margin")}>
        <table className="min-w-full text-[13px]">
          <thead className="border-b border-slate-200"><tr><Th>{t("pf.col.project")}</Th><Th right>{t("pf.chart.bid")}</Th><Th right>{t("pf.chart.forecast")}</Th><Th right>{t("pf.d.change")}</Th></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {[...scope].sort((a, b) => b.margin_erosion_pts - a.margin_erosion_pts).map((p) => (
              <tr key={p.code}><Td>{projectLink(p)}</Td><Td right>{pct(p.bid_margin_pct, lang)}</Td><Td right className="font-semibold">{pct(p.forecast_margin_pct, lang)}</Td>
                <Td right className={p.margin_erosion_pts > 0.03 ? "text-red-700" : p.margin_erosion_pts < 0 ? "text-emerald-700" : ""}>{pts(-p.margin_erosion_pts, lang)}</Td></tr>
            ))}
          </tbody>
        </table>
      </DetailDrawer>

      <DetailDrawer open={detail === "pending"} onClose={() => setDetail(null)} title={t("pf.kpi.pending")} explain={t("pf.d.pending")}>
        {!pendingCos ? <Loading /> : (
          <table className="min-w-full text-[13px]">
            <thead className="border-b border-slate-200"><tr><Th>{t("pf.col.project")}</Th><Th>{t("pj.col.description")}</Th><Th right>USD</Th><Th right>{t("pj.col.pending_days")}</Th><Th /></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {pendingCos.map((c) => (
                <tr key={`${c.project}-${c.number}`}>
                  <Td className="whitespace-nowrap"><button onClick={() => go(c.project)} className="font-semibold text-[#2a78d6] hover:underline">{c.project}</button> <span className="text-slate-500">{c.number}</span></Td>
                  <Td className="max-w-[260px] text-slate-700">{c.titles[lang]}</Td>
                  <Td right className="font-medium">{money(c.amount_usd, lang)}</Td>
                  <Td right className={clsx((c.days_pending ?? 0) > 90 && "font-semibold text-violet-700")}>{c.days_pending}</Td>
                  <Td><SourceLink document_id={c.document_id} locator={c.locator}>PDF</SourceLink></Td>
                </tr>
              ))}
              <tr className="bg-slate-50 font-semibold">
                <Td>{t("pj.col.total")}</Td><Td /><Td right>{money(pendingCos.reduce((a, c) => a + c.amount_usd, 0), lang)}</Td><Td /><Td />
              </tr>
            </tbody>
          </table>
        )}
      </DetailDrawer>
    </>
  );
}
