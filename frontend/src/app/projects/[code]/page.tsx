"use client";

import clsx from "clsx";
import { ChevronLeft, FileSpreadsheet, FileText, GanttChart } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import Chart, { ChartOption } from "@/components/Chart";
import { useApp } from "@/components/providers";
import { Badge, DetailDrawer, Card, ErrorState, Flags, HealthBadge, Loading, ProgressBar, Segmented, SourceLink, Stat, Td, Th } from "@/components/ui";
import type { ProjectDetail } from "@/lib/api";
import { axisBase, C, legendBase, tooltipBase } from "@/lib/chartTheme";
import { date, money, pct, period, pts, ratio } from "@/lib/format";
import { useApi } from "@/lib/useApi";

type Conv = { conv: (x: number) => number; cur: string };

function Waterfall({ d, conv, cur }: { d: ProjectDetail } & Conv) {
  const { t, lang, label } = useApp();
  const option = useMemo<ChartOption>(() => {
    const steps = d.waterfall.steps;
    const names: string[] = [], base: number[] = [], vals: number[] = [], colors: string[] = [], raw: number[] = [];
    let running = 0;
    steps.forEach((s, i) => {
      const v = conv(s.value);
      const name = s.key === "activity" ? label("activities", s.code) : t(`pj.wf.${s.key}`);
      names.push(name);
      raw.push(v);
      const isTotal = i === 0 || i === steps.length - 1;
      if (isTotal) {
        base.push(v < 0 ? v : 0);
        vals.push(Math.abs(v));
        colors.push(v < 0 ? C.red : C.blue550);
        running = v;
      } else if (v >= 0) {
        base.push(running);
        vals.push(v);
        colors.push(C.blue300);
        running += v;
      } else {
        running += v;
        base.push(running);
        vals.push(-v);
        colors.push(C.red);
      }
    });
    const pending = conv(d.waterfall.pending_recovery);
    if (pending > 0) {
      names.push(t("pj.wf.pending"));
      base.push(running);
      vals.push(pending);
      colors.push("rgba(42,120,214,0.10)");
      raw.push(pending);
    }
    const revised = conv(d.waterfall.revised_contract);
    // Horizontal waterfall: bid margin at the top, forecast margin at the bottom, so activity names have room.
    return {
      grid: { left: 150, right: 64, top: 8, bottom: 24 },
      tooltip: {
        ...tooltipBase, trigger: "axis", axisPointer: { type: "shadow", shadowStyle: { color: "rgba(0,0,0,0.03)" } },
        formatter: (ps: { dataIndex: number }[]) => {
          const i = ps[0].dataIndex;
          return `<b>${names[i]}</b><br/>${money(raw[i], lang, cur)} · ${pts(raw[i] / revised, lang)}`;
        },
      },
      yAxis: { type: "category", data: names, inverse: true, ...axisBase, splitLine: { show: false }, axisLabel: { color: C.ink2, fontSize: 12 } },
      xAxis: { type: "value", ...axisBase, axisLabel: { ...axisBase.axisLabel, formatter: (v: number) => money(v, lang, cur).replace(/^\S+ /, "") } },
      series: [
        { type: "bar", stack: "w", data: base, itemStyle: { color: "transparent" }, emphasis: { disabled: true }, tooltip: { show: false }, barWidth: 18 },
        {
          type: "bar", stack: "w", barWidth: 18,
          data: vals.map((v, i) => ({
            value: v,
            itemStyle: {
              color: colors[i], borderRadius: 4,
              ...(pending > 0 && i === vals.length - 1 ? { borderColor: C.s1, borderWidth: 1.5, borderType: "dashed" } : {}),
            },
          })),
          label: {
            show: true, position: "right", fontSize: 11, color: C.ink2,
            formatter: (p: { dataIndex: number }) => {
              const v = raw[p.dataIndex];
              const first = p.dataIndex === 0 || p.dataIndex === steps.length - 1;
              return first ? pct(v / (p.dataIndex === 0 ? conv(d.waterfall.revised_contract - d.kpis.approved_co_value) : revised), lang) : money(v, lang, cur).replace(/^\S+ /, v > 0 ? "+" : "");
            },
          },
        },
      ],
    };
  }, [d, conv, cur, lang, t, label]);

  const pending = d.change_orders.filter((c) => c.status === "pending");
  return (
    <div className="grid gap-5 lg:grid-cols-3">
      <div className="lg:col-span-2">
        <Chart option={option} height={d.waterfall.steps.length * 36 + 70} ariaLabel={t("pj.s.waterfall")} />
        {pending.length > 0 && (
          <p className="mt-2 text-[13px] text-slate-600">
            {t(pending.length === 1 ? "pj.wf.pending_note1" : "pj.wf.pending_note", {
              n: pending.length, v: money(conv(d.waterfall.pending_recovery), lang, cur),
              m: pct((d.kpis.forecast_margin_value + d.waterfall.pending_recovery) / (d.kpis.revised_contract + d.waterfall.pending_recovery), lang),
            })}
          </p>
        )}
      </div>
      <div>
        <h3 className="mb-2 text-[13px] font-semibold text-slate-900">{t("pj.s.drivers")}</h3>
        <ol className="space-y-3">
          {d.drivers.map((dr, i) => (
            <li key={dr.activity} className="rounded-lg bg-slate-50 p-3 ring-1 ring-slate-100">
              <p className="text-[13px] font-semibold text-slate-900">{i + 1}. {label("activities", dr.activity)}</p>
              <p className="mt-0.5 text-[12.5px] text-red-700">{t("pj.drv.over", { v: money(conv(dr.variance), lang, cur), s: pct(dr.share, lang, 0) })}</p>
              {dr.cos.length > 0 && (
                <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[12px] text-slate-600">
                  {t("pj.drv.cos")}
                  {dr.cos.map((n) => {
                    const co = d.change_orders.find((c) => c.number === n);
                    return co ? <SourceLink key={n} document_id={co.document_id} locator={co.locator}>{n}</SourceLink> : null;
                  })}
                </div>
              )}
              {dr.days_lost > 0 && <p className="mt-1 text-[12px] text-slate-600">{t("pj.drv.days", { d: dr.days_lost, v: money(conv(dr.standby_cost), lang, cur) })}</p>}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

function SCurve({ d, conv, cur }: { d: ProjectDetail } & Conv) {
  const { t, lang } = useApp();
  const option = useMemo<ChartOption>(() => {
    const pts_ = d.scurve;
    const x = pts_.map((p) => period(p.period, lang));
    const line = (name: string, color: string, vals: (number | null)[]) => ({
      name, type: "line", data: vals.map((v) => (v === null ? null : conv(v))), showSymbol: false, symbolSize: 8,
      lineStyle: { width: 2, color }, itemStyle: { color },
    });
    return {
      grid: { left: 64, right: 24, top: 34, bottom: 28 },
      legend: { ...legendBase, data: [t("pj.pv"), t("pj.ev"), t("pj.ac")] },
      tooltip: {
        ...tooltipBase, trigger: "axis",
        valueFormatter: (v: number) => money(v, lang, cur),
      },
      xAxis: { type: "category", data: x, boundaryGap: false, ...axisBase, splitLine: { show: false } },
      yAxis: {
        type: "value", ...axisBase, max: (v: { max: number }) => Math.max(v.max, conv(d.kpis.bac), conv(d.kpis.eac)) * 1.06,
        axisLabel: { ...axisBase.axisLabel, formatter: (v: number) => money(v, lang, cur).replace(/^\S+ /, "") },
      },
      series: [
        {
          ...line(t("pj.pv"), C.s1, pts_.map((p) => p.pv)),
          markLine: {
            symbol: "none", silent: true,
            data: [
              { yAxis: conv(d.kpis.bac), lineStyle: { color: C.axis, type: "solid", width: 1 }, label: { formatter: `${t("pj.bac")} ${money(conv(d.kpis.bac), lang, cur)}`, color: C.muted, fontSize: 11, position: d.kpis.eac >= d.kpis.bac ? "insideStartBottom" : "insideStartTop" } },
              ...(d.project.status === "active" ? [{ yAxis: conv(d.kpis.eac), lineStyle: { color: C.s2, type: "dashed", width: 1 }, label: { formatter: `${t("pj.eac")} ${money(conv(d.kpis.eac), lang, cur)}`, color: C.s2, fontSize: 11, position: d.kpis.eac >= d.kpis.bac ? "insideEndTop" : "insideEndBottom" } }] : []),
            ],
          },
        },
        line(t("pj.ev"), C.s3, pts_.map((p) => p.ev)),
        line(t("pj.ac"), C.s2, pts_.map((p) => p.ac)),
      ],
    };
  }, [d, conv, cur, lang, t]);
  return <Chart option={option} height={320} ariaLabel={t("pj.s.scurve")} />;
}

function Gantt({ d }: { d: ProjectDetail }) {
  const { t, lang, label } = useApp();
  const option = useMemo<ChartOption>(() => {
    const tasks = d.schedule;
    const ts = (s: string) => Date.parse(`${s}T00:00:00Z`);
    const names = tasks.map((tk) => (tk.activity ? label("activities", tk.activity) : tk.name));
    const statusTs = ts(`${d.project.as_of_period}-28`);
    const all = tasks.flatMap((tk) => [ts(tk.baseline_start), ts(tk.baseline_finish), ts(tk.start), ts(tk.finish)]);
    const month = 31 * 86400000;
    return {
      grid: { left: 170, right: 24, top: 46, bottom: 28 },
      legend: { ...legendBase, data: [t("pj.baseline"), t("pj.actual_forecast")] },
      tooltip: {
        ...tooltipBase, trigger: "item",
        formatter: (p: { dataIndex: number }) => {
          const tk = tasks[p.dataIndex];
          return `<b>${names[p.dataIndex]}</b><br/>${t("pj.baseline")}: ${date(tk.baseline_start, lang)} → ${date(tk.baseline_finish, lang)}<br/>${t("pj.actual_forecast")}: ${date(tk.start, lang)} → ${date(tk.finish, lang)}<br/>${pct(tk.pct, lang, 0)}`;
        },
      },
      xAxis: { type: "time", min: Math.min(...all) - month / 2, max: Math.max(...all, statusTs) + month / 2, splitNumber: 6, ...axisBase, axisLabel: { ...axisBase.axisLabel, hideOverlap: true, formatter: (v: number) => new Intl.DateTimeFormat(lang, { month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(v)) } },
      yAxis: { type: "category", data: names, inverse: true, ...axisBase, axisLabel: { color: C.ink2, fontSize: 11 }, splitLine: { show: false } },
      series: [
        // legend-only entries (lines add no extent to the time axis, unlike bars)
        { name: t("pj.baseline"), type: "line", data: [], itemStyle: { color: C.bidGray } },
        { name: t("pj.actual_forecast"), type: "line", data: [], itemStyle: { color: C.s1 } },
        {
          type: "custom",
          data: tasks.map((tk, i) => [i, ts(tk.baseline_start), ts(tk.baseline_finish), ts(tk.start), ts(tk.finish), tk.pct]),
          encode: { x: [1, 2, 3, 4], y: 0 },
          renderItem: (_params: unknown, api: { value: (i: number) => number; coord: (v: number[]) => number[]; size: (v: number[]) => number[] }) => {
            const y = api.value(0);
            const h = api.size([0, 1])[1];
            const [bx0, by] = api.coord([api.value(1), y]);
            const [bx1] = api.coord([api.value(2), y]);
            const [ax0] = api.coord([api.value(3), y]);
            const [ax1] = api.coord([api.value(4), y]);
            const done = ax0 + (ax1 - ax0) * api.value(5);
            return {
              type: "group",
              children: [
                { type: "rect", shape: { x: bx0, y: by - h * 0.3, width: Math.max(bx1 - bx0, 2), height: 4, r: 2 }, style: { fill: C.bidGray } },
                { type: "rect", shape: { x: ax0, y: by - h * 0.3 + 7, width: Math.max(ax1 - ax0, 2), height: 8, r: 4 }, style: { fill: "#cde2fb" } },
                { type: "rect", shape: { x: ax0, y: by - h * 0.3 + 7, width: Math.max(done - ax0, 0), height: 8, r: 4 }, style: { fill: C.s1 } },
              ],
            };
          },
          markLine: { symbol: "none", silent: true, data: [{ xAxis: statusTs }], lineStyle: { color: C.ink2, type: "solid", width: 1 }, label: { formatter: `${t("pj.today")} · ${period(d.project.as_of_period, lang)}`, position: "start", distance: 6, color: C.ink2, fontSize: 11 } }, // y axis is inverted: "start" is the top
        },
      ],
    };
  }, [d, lang, t, label]);
  return <Chart option={option} height={Math.max(260, d.schedule.length * 30 + 60)} ariaLabel={t("pj.s.schedule")} />;
}

function Production({ d }: { d: ProjectDetail }) {
  const { t, lang } = useApp();
  const x = d.production.map((p) => period(p.period, lang));
  const km = useMemo<ChartOption>(() => ({
    grid: { left: 44, right: 16, top: 16, bottom: 28 },
    tooltip: { ...tooltipBase, trigger: "axis", valueFormatter: (v: number) => `${v.toFixed(1)} km` },
    xAxis: { type: "category", data: x, boundaryGap: false, ...axisBase, splitLine: { show: false } },
    yAxis: { type: "value", max: d.project.length_km ?? undefined, ...axisBase },
    series: [{ type: "line", data: d.production.map((p) => p.km), showSymbol: false, lineStyle: { width: 2, color: C.s1 }, itemStyle: { color: C.s1 }, areaStyle: { color: "rgba(42,120,214,0.08)" } }],
  }), [d, x]);
  const rep = useMemo<ChartOption>(() => ({
    grid: { left: 44, right: 16, top: 16, bottom: 28 },
    tooltip: { ...tooltipBase, trigger: "axis", valueFormatter: (v: number) => pct(v, lang) },
    xAxis: { type: "category", data: x, ...axisBase, splitLine: { show: false } },
    yAxis: { type: "value", ...axisBase, axisLabel: { ...axisBase.axisLabel, formatter: (v: number) => pct(v, lang, 0) } },
    series: [{
      type: "bar", barWidth: "55%",
      data: d.production.map((p) => ({ value: p.repair_rate, itemStyle: { color: (p.repair_rate ?? 0) > 0.05 ? C.critical : C.s1, borderRadius: [4, 4, 0, 0] } })),
      markLine: { symbol: "none", silent: true, data: [{ yAxis: 0.05 }], lineStyle: { color: C.critical, type: "solid", width: 1 }, label: { formatter: t("pj.repair_limit"), color: C.critical, fontSize: 11, position: "insideEndTop" } },
    }],
  }), [d, x, lang, t]);
  return (
    <div className="grid gap-5 md:grid-cols-2">
      <div><p className="text-[12px] font-medium text-slate-500">{t("pj.km")}</p><Chart option={km} height={220} ariaLabel={t("pj.km")} /></div>
      <div><p className="text-[12px] font-medium text-slate-500">{t("pj.repair")}</p><Chart option={rep} height={220} ariaLabel={t("pj.repair")} /></div>
    </div>
  );
}

function AnomaliesCard({ d, conv, cur }: { d: ProjectDetail } & Conv) {
  const { t, lang, label } = useApp();
  if (!d.anomalies.length) return null;
  const max = Math.max(...d.anomalies.map((a) => a.excess), 1);
  return (
    <Card title={t("pj.s.anomalies")} subtitle={t("pj.s.anomalies_sub")} bodyClass="px-0 pb-2">
      <div className="divide-y divide-slate-100">
        {d.anomalies.map((a, i) => (
          <div key={i} className="grid grid-cols-[92px_minmax(0,1fr)_110px] items-center gap-3 px-5 py-2.5 text-[13px]">
            <span className="text-slate-600">{period(a.period, lang)}</span>
            <div className="min-w-0">
              <p className="truncate font-medium text-slate-800">{label("activities", a.activity)}</p>
              <div className="mt-1 flex items-center gap-2">
                <div className="h-1.5 flex-1 rounded-full bg-slate-100">
                  <div className={clsx("h-1.5 rounded-full", a.explanation ? "bg-[#6da7ec]" : "bg-[#d03b3b]")} style={{ width: `${(a.excess / max) * 100}%` }} />
                </div>
                {a.explanation ? (
                  <SourceLink document_id={a.explanation.document_id} locator={a.explanation.locator} className="shrink-0">
                    {a.explanation.kind === "issue" ? label("issue_categories", a.explanation.category) : a.explanation.number}
                  </SourceLink>
                ) : <Badge tone="red">{t("dh.unexplained")}</Badge>}
                <SourceLink document_id={a.document_id} locator={a.locator} className="shrink-0">{t("dh.src.excel")}</SourceLink>
              </div>
            </div>
            <p className="text-right font-medium tabular-nums text-slate-900">+{money(conv(a.excess), lang, cur)}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}

function ErpCard({ d }: { d: ProjectDetail }) {
  const { t, lang, label } = useApp();
  const e = d.erp;
  return (
    <Card title={t("pj.s.erp")}>
      {!e.cells ? <p className="text-[13px] text-slate-500">{t("pj.erp_none")}</p> : (
        <div className="space-y-3">
          <p className="flex items-center gap-2 text-[13px] text-slate-600">
            {e.discrepancies.length ? <Badge tone="amber">{e.discrepancies.length}</Badge> : <Badge tone="green">{t("pj.all_ok")}</Badge>}
            {t("pj.erp_stats", { matched: e.matched, cells: e.cells, rate: pct(e.match_rate, lang) })}
          </p>
          {e.discrepancies.map((x, i) => (
            <div key={i} className="rounded-lg bg-amber-50/60 p-3 ring-1 ring-amber-100">
              <p className="text-[13px] font-medium text-slate-900">{t(`dh.f.${x.kind}`)}</p>
              <p className="text-[12.5px] text-slate-600">{period(x.period, lang)} · {label("cost_types", x.cost_type)} · {t("dh.f.erp_detail", { erp: money(x.erp_amount, lang, x.currency), excel: money(x.excel_amount, lang, x.currency) })}
                {x.erp_rows[0] && x.kind !== "missing_in_erp" ? ` · ${x.erp_rows[0].reference}${x.erp_rows[0].vendor ? ` (${x.erp_rows[0].vendor})` : ""}` : ""}</p>
              <div className="mt-1 flex gap-3">
                {x.erp_rows[0] && <SourceLink document_id={x.erp_rows[0].document_id} locator={x.erp_rows[0].locator}>{t("dh.src.erp")}</SourceLink>}
                {x.excel_cells[0] && <SourceLink document_id={x.excel_cells[0].document_id} locator={x.excel_cells[0].locator}>{t("dh.src.excel")}</SourceLink>}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

const CO_TONE = { approved: "green", pending: "violet", rejected: "red" } as const;

export default function ProjectPage() {
  const { code } = useParams<{ code: string }>();
  const { t, lang, label, country, openSource } = useApp();
  const { data: d, error, loading, reload } = useApi<ProjectDetail>(`/api/projects/${code}`);
  const [curMode, setCurMode] = useState<"local" | "usd">("local");
  const [detail, setDetail] = useState<null | "cost" | "schedule">(null);

  const fx = d?.project.fx_usd ?? 1;
  const useUsd = curMode === "usd" && d?.project.currency !== "USD";
  const cur = useUsd ? "USD" : d?.project.currency ?? "USD";
  const conv = useMemo(() => (x: number) => (useUsd ? x * fx : x), [useUsd, fx]);

  if (error && !d) return <ErrorState message={error === "Project not found" ? t("pj.notfound") : error} onRetry={reload} />;
  if (loading || !d) return <Loading />;
  const p = d.project, k = d.kpis;
  const closed = p.status === "closed";
  const totals = d.activities.reduce((a, x) => ({ bac: a.bac + x.bac, ac: a.ac + x.ac, eac: a.eac + x.eac }), { bac: 0, ac: 0, eac: 0 });
  const jump = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  const worked = d.activities.filter((a) => a.ac > 0 || a.pv > 0);

  return (
    <div className="space-y-6">
      <div>
        <Link href="/" className="mb-3 inline-flex items-center gap-1 text-[13px] text-slate-500 hover:text-slate-900"><ChevronLeft className="h-4 w-4" /> {t("pj.back")}</Link>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{p.code} · {p.name}</h1>
              <HealthBadge health={k.health} />
              <Badge>{t(`status.${p.status}`)}</Badge>
            </div>
            <p className="mt-1 max-w-3xl text-sm text-slate-500">{p.descriptions[lang]}</p>
            <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-[13px] text-slate-600">
              <span><b className="font-medium text-slate-400">{t("pj.client")}</b> {p.client}</span>
              <span>{country(p.country)} · {p.region}</span>
              <span><b className="font-medium text-slate-400">{t("pj.terrain")}</b> {label("terrains", p.terrain)}</span>
              {p.kind === "pipeline" && <span><b className="font-medium text-slate-400">{t("pj.scope")}</b> {p.diameter_in}&quot; × {p.length_km} km</span>}
              <span><b className="font-medium text-slate-400">{t("pj.dates")}</b> {period(p.start_period, lang)} → {period(p.planned_finish, lang)}
                {k.delay_months > 0 && <> · <span className="font-medium text-amber-700">{t("pj.delay", { n: k.delay_months })}</span></>}</span>
              <span>{t(`ct.${p.contract_type}`)}</span>
              <span><b className="font-medium text-slate-400">{t("pj.manager")}</b> {p.manager}</span>
            </div>
            <div className="mt-2"><Flags flags={k.flags} max={6} /></div>
          </div>
          {p.currency !== "USD" && (
            <Segmented value={curMode} onChange={setCurMode} size="sm" options={[{ value: "local", label: `${t("pj.currency.local")} (${p.currency})` }, { value: "usd", label: "USD" }]} />
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <Stat label={t("pj.k.contract")} value={money(conv(p.contract_value), lang, cur)} sub={t("pj.k.revised", { v: money(conv(k.revised_contract), lang, cur) })} source={p.contract_source}
          onClick={p.contract_source.document_id ? () => openSource({ kind: "source", document_id: p.contract_source.document_id!, locator: p.contract_source.locator }) : undefined} />
        <Stat label={closed ? t("pj.k.final_cost") : t("pj.k.eac")} value={money(conv(k.eac), lang, cur)} tone={k.cost_overrun_pct > 0.03 ? "red" : undefined} sub={t("pj.k.eac_sub", { v: money(conv(k.bac), lang, cur) })} onClick={() => jump("activities")} />
        <Stat label={closed ? t("pj.k.final_margin") : t("pj.k.margin")} value={pct(k.forecast_margin_pct, lang)} tone={k.margin_erosion_pts >= 0.03 ? "red" : k.margin_erosion_pts < 0 ? "green" : undefined}
          sub={<>{t("pj.k.bid", { v: pct(k.bid_margin_pct, lang) })} · {pts(-k.margin_erosion_pts, lang)}</>} source={p.bid_margin_source} onClick={() => jump("margin")} />
        {!closed ? (
          <>
            <Stat label={t("pj.k.cpi")} value={ratio(k.cpi)} tone={k.cpi !== null && k.cpi < 0.95 ? "red" : "green"} sub={t("pj.k.cpi_sub", { v: ratio(k.cpi) })} onClick={() => setDetail("cost")} />
            <Stat label={t("pj.k.spi")} value={ratio(k.spi)} tone={k.spi !== null && k.spi < 0.92 ? "amber" : "green"} sub={t("pj.k.spi_sub", { v: pct(k.spi, lang, 0) })} onClick={() => setDetail("schedule")} />
          </>
        ) : (
          <>
            <Stat label={t("pj.dates")} value={`${k.delay_months} ${t("common.months")}`} tone={k.delay_months >= 3 ? "amber" : undefined} sub={`${period(p.planned_finish, lang)} → ${period(p.forecast_finish, lang)}`} onClick={() => jump("schedule")} />
            <Stat label={t("pj.s.issues")} value={`${d.issues.reduce((a, i) => a + i.days_lost, 0)} ${t("common.days")}`} sub={`${d.issues.length} · ${money(conv(d.issues.reduce((a, i) => a + i.cost_impact, 0)), lang, cur)}`} onClick={() => jump("issues")} />
          </>
        )}
        <Stat label={t("pj.k.pending")} value={money(conv(k.pending_co_value), lang, cur)} tone={k.pending_co_count ? "amber" : undefined}
          sub={k.pending_co_count ? t(k.pending_co_count === 1 ? "pj.k.pending_sub1" : "pj.k.pending_sub", { n: k.pending_co_count, d: k.oldest_pending_days }) : "—"}
          onClick={() => jump("change-orders")} />
      </div>
      {!closed && (
        <div role="button" tabIndex={0} onClick={() => setDetail("schedule")} onKeyDown={(e) => e.key === "Enter" && setDetail("schedule")}
          className="cursor-pointer rounded-xl bg-white p-4 ring-1 ring-black/[0.07] transition-shadow hover:shadow-md hover:ring-[#2a78d6]/40">
          <div className="mb-2 flex justify-between text-[12px] text-slate-500">
            <span>{t("pj.k.progress")}: <b className="text-slate-900">{pct(k.progress_pct, lang)}</b></span>
            <span>{t("pj.k.progress_sub", { v: pct(k.planned_pct, lang) })}</span>
          </div>
          <ProgressBar actual={k.progress_pct} planned={k.planned_pct} className="h-2.5" />
        </div>
      )}

      <Card id="margin" title={t("pj.s.waterfall")} subtitle={t("pj.s.waterfall_sub", { cur })}>
        <Waterfall d={d} conv={conv} cur={cur} />
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card title={t("pj.s.scurve")} subtitle={t("pj.s.scurve_sub", { cur })}><SCurve d={d} conv={conv} cur={cur} /></Card>
        <Card id="schedule" title={t("pj.s.schedule")}>{d.schedule.length ? <Gantt d={d} /> : <p className="text-sm text-slate-400">{t("pj.none")}</p>}</Card>
      </div>

      <Card id="activities" title={t("pj.s.activities")} subtitle={t("pj.s.activities_sub")} bodyClass="px-0 pb-2">
        <div className="overflow-x-auto">
          <table className="min-w-full text-[13px]">
            <thead className="border-y border-slate-100 bg-slate-50/60">
              <tr>
                <Th>{t("pj.col.activity")}</Th><Th right>{t("pj.col.budget")}</Th><Th right>{t("pj.col.actual")}</Th>
                <Th>{t("pj.col.progress")}</Th><Th right>{t("pj.col.cpi")}</Th><Th right>{t("pj.col.eac")}</Th><Th right>{t("pj.col.variance")}</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {d.activities.map((a) => (
                <tr key={a.code} className="cursor-pointer hover:bg-blue-50/40" onClick={() => openSource({ kind: "activity", project: p.code, activity: a.code })}>
                  <Td>
                    <span className="font-medium text-slate-900">{a.names[lang]}</span>
                    {a.budget_co > 0 && <Badge tone="violet" className="ml-2">{t("pj.badge_co")}</Badge>}
                  </Td>
                  <Td right>{money(conv(a.bac), lang, cur)}</Td>
                  <Td right>{money(conv(a.ac), lang, cur)}</Td>
                  <Td className="w-40"><ProgressBar actual={a.pct} planned={closed ? undefined : a.planned} /><span className="text-[11px] text-slate-400">{pct(a.pct, lang, 0)}</span></Td>
                  <Td right className={clsx(a.cpi !== null && a.cpi < 0.9 && "text-red-700")}>{closed || a.pct < 0.1 ? "–" : ratio(a.cpi)}</Td>
                  <Td right>{money(conv(a.eac), lang, cur)}</Td>
                  <Td right className={clsx("font-medium", a.variance > 0 ? "text-red-700" : "text-emerald-700")}>{a.variance > 0 ? "+" : ""}{money(conv(a.variance), lang, cur)}</Td>
                </tr>
              ))}
              <tr className="bg-slate-50 font-semibold">
                <Td>{t("pj.col.total")}</Td><Td right>{money(conv(totals.bac), lang, cur)}</Td><Td right>{money(conv(totals.ac), lang, cur)}</Td>
                <Td /><Td right>{ratio(k.cpi)}</Td><Td right>{money(conv(totals.eac), lang, cur)}</Td>
                <Td right className={totals.eac > totals.bac ? "text-red-700" : "text-emerald-700"}>{money(conv(totals.eac - totals.bac), lang, cur)}</Td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid gap-6 xl:grid-cols-5">
        <div className="xl:col-span-3"><AnomaliesCard d={d} conv={conv} cur={cur} /></div>
        <div className="xl:col-span-2"><ErpCard d={d} /></div>
      </div>

      <Card id="change-orders" title={t("pj.s.cos")} bodyClass="px-0 pb-2">
        {d.change_orders.length === 0 ? <p className="px-5 text-sm text-slate-400">{t("pj.none")}</p> : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-[13px]">
              <thead className="border-y border-slate-100 bg-slate-50/60">
                <tr><Th>{t("pj.col.number")}</Th><Th>{t("pj.col.description")}</Th><Th>{t("pj.col.cause")}</Th><Th right>{t("pj.col.amount")}</Th><Th>{t("pj.col.status")}</Th><Th right>{t("pj.col.pending_days")}</Th><Th>{t("pj.col.doc")}</Th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {d.change_orders.map((c) => (
                  <tr key={c.id}>
                    <Td className="font-semibold text-slate-900">{c.number}</Td>
                    <Td className="max-w-md"><p className="text-slate-700">{c.titles[lang]}</p><p className="text-[12px] text-slate-400">{label("activities", c.activity)} · {date(c.submitted_date, lang)}</p></Td>
                    <Td className="text-slate-600">{label("co_causes", c.cause)}</Td>
                    <Td right className="font-medium">{money(useUsd ? c.amount_usd : c.amount, lang, cur)}</Td>
                    <Td><Badge tone={CO_TONE[c.status]}>{label("co_status", c.status)}</Badge></Td>
                    <Td right className={clsx(c.days_pending && c.days_pending > 90 && "font-semibold text-violet-700")}>{c.days_pending ?? "—"}</Td>
                    <Td><SourceLink document_id={c.document_id} locator={c.locator}>PDF</SourceLink></Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card id="issues" title={t("pj.s.issues")} bodyClass="px-0 pb-2">
        {d.issues.length === 0 ? <p className="px-5 text-sm text-slate-400">{t("pj.none")}</p> : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-[13px]">
              <thead className="border-y border-slate-100 bg-slate-50/60">
                <tr><Th>{t("pj.col.month")}</Th><Th>{t("pj.col.category")}</Th><Th>{t("pj.col.description")}</Th><Th right>{t("pj.col.days_lost")}</Th><Th right>{t("pj.col.impact")}</Th><Th>{t("pj.col.doc")}</Th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {d.issues.map((i) => (
                  <tr key={i.id}>
                    <Td className="whitespace-nowrap text-slate-600">{period(i.period, lang)}</Td>
                    <Td><Badge tone={i.category === "community" || i.category === "permits" ? "violet" : i.category === "weather" ? "blue" : "amber"}>{label("issue_categories", i.category)}</Badge></Td>
                    <Td className="max-w-xl text-slate-700">{i.descriptions[lang]}</Td>
                    <Td right>{i.days_lost}</Td>
                    <Td right>{money(conv(i.cost_impact), lang, cur)}</Td>
                    <Td><SourceLink document_id={i.document_id} locator={i.locator}>{i.locator}</SourceLink></Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {d.production.length > 0 && <Card title={t("pj.s.production")}><Production d={d} /></Card>}

      <Card title={`${t("pj.s.documents")} (${d.documents.length})`}>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {d.documents.map((doc) => {
            const Icon = doc.doc_type.includes("workbook") ? FileSpreadsheet : doc.doc_type === "schedule" ? GanttChart : FileText;
            return (
              <button key={doc.id} onClick={() => openSource({ kind: "source", document_id: doc.id, locator: doc.pages ? "p.1" : null })}
                className="flex items-center gap-3 rounded-lg p-2.5 text-left ring-1 ring-slate-200 hover:bg-slate-50">
                <Icon className="h-5 w-5 shrink-0 text-[#1f3a5f]" />
                <span className="min-w-0">
                  <span className="block truncate text-[13px] font-medium text-slate-800">{doc.title}</span>
                  <span className="block truncate text-[11.5px] text-slate-400">{t(`doc.${doc.doc_type}`)} · {doc.filename}</span>
                </span>
                {doc.origin === "upload" && <Badge tone="violet" className="ml-auto">{t("pj.uploaded")}</Badge>}
              </button>
            );
          })}
        </div>
      </Card>
      <DetailDrawer open={detail === "cost"} onClose={() => setDetail(null)} title={`${t("pj.k.cpi")}: ${ratio(k.cpi)}`} explain={t("pj.d.cost")}>
        <table className="min-w-full text-[13px]">
          <thead className="border-b border-slate-200"><tr><Th>{t("pj.col.activity")}</Th><Th right>{t("pj.ev")}</Th><Th right>{t("pj.ac")}</Th><Th right>{t("pj.col.cpi")}</Th></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {worked.map((a) => (
              <tr key={a.code} className="cursor-pointer hover:bg-blue-50/40" onClick={() => openSource({ kind: "activity", project: p.code, activity: a.code })}>
                <Td className="font-medium text-slate-800">{a.names[lang]}</Td>
                <Td right>{money(conv(a.ev), lang, cur)}</Td>
                <Td right>{money(conv(a.ac), lang, cur)}</Td>
                <Td right className={clsx("font-semibold", a.cpi !== null && a.cpi < 0.9 ? "text-red-700" : "text-slate-900")}>{a.pct < 0.1 ? "–" : ratio(a.cpi)}</Td>
              </tr>
            ))}
            <tr className="bg-slate-50 font-semibold">
              <Td>{t("pj.col.total")}</Td><Td right>{money(conv(k.ev), lang, cur)}</Td><Td right>{money(conv(k.ac), lang, cur)}</Td><Td right>{ratio(k.cpi)}</Td>
            </tr>
          </tbody>
        </table>
        <p className="mt-3 text-[12px] text-slate-400">{t("pj.d.cost_note")}</p>
      </DetailDrawer>

      <DetailDrawer open={detail === "schedule"} onClose={() => setDetail(null)} title={`${t("pj.k.spi")}: ${ratio(k.spi)}`} explain={t("pj.d.schedule")}>
        <table className="min-w-full text-[13px]">
          <thead className="border-b border-slate-200"><tr><Th>{t("pj.col.activity")}</Th><Th right>{t("pj.d.planned")}</Th><Th right>{t("pj.d.actual")}</Th><Th right>{t("pj.d.gap")}</Th></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {worked.map((a) => (
              <tr key={a.code}>
                <Td className="font-medium text-slate-800">{a.names[lang]}</Td>
                <Td right>{pct(a.planned, lang, 0)}</Td>
                <Td right>{pct(a.pct, lang, 0)}</Td>
                <Td right className={clsx("font-semibold", a.pct < a.planned - 0.05 ? "text-amber-700" : "text-slate-900")}>{pts(a.pct - a.planned, lang)}</Td>
              </tr>
            ))}
            <tr className="bg-slate-50 font-semibold">
              <Td>{t("pj.col.total")}</Td><Td right>{pct(k.planned_pct, lang, 0)}</Td><Td right>{pct(k.progress_pct, lang, 0)}</Td><Td right>{pts(k.progress_pct - k.planned_pct, lang)}</Td>
            </tr>
          </tbody>
        </table>
        <button onClick={() => { setDetail(null); jump("schedule"); }} className="mt-4 text-[13px] font-medium text-[#2a78d6] hover:underline">{t("pj.d.see_schedule")}</button>
      </DetailDrawer>
    </div>
  );
}
