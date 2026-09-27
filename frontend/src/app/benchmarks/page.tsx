"use client";

import clsx from "clsx";
import { Calculator, ChevronRight, Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import Chart, { ChartOption } from "@/components/Chart";
import { useApp } from "@/components/providers";
import { Badge, Card, DetailDrawer, ErrorState, Loading, PageHeader, Segmented, Select, Td, Th } from "@/components/ui";
import { api } from "@/lib/api";
import { axisBase, C, legendBase, TERRAIN_COLOR, tooltipBase } from "@/lib/chartTheme";
import { money, num, pct, period, pts } from "@/lib/format";
import { useApi } from "@/lib/useApi";

type Terrain = "coast" | "highlands" | "rainforest";
const TERRAINS: Terrain[] = ["coast", "highlands", "rainforest"];

interface Point {
  code: string; name: string; country: string; terrain: Terrain; diameter_in: number; length_km: number; finish_period: string; origin: string;
  final_cost_usd: number; cost_per_km_usd: number; cost_per_inch_km_usd: number; overrun_pct: number | null;
  bid_margin_pct: number; final_margin_pct: number; margin_delta_pts: number; duration_months: number; delay_months: number;
  welding_m_per_day: number | null;
}
interface Bench {
  points: Point[];
  by_terrain: Record<Terrain, { n: number; cost_per_inch_km_p50: number; cost_per_km_p50: number; overrun_p50: number; margin_delta_p50: number; delay_p50: number; welding_m_per_day_p50: number | null }>;
  activity_overrun: Record<Terrain, Record<string, number | null>>;
  base_year: number;
  escalation: number;
}
interface Estimate {
  cost_p25: number; cost_p50: number; cost_p75: number; contingency_pct: number; cost_with_contingency: number;
  suggested_price: number; price_per_km: number; sample: string[]; note: string | null; historical_margin_delta: number;
}

export default function BenchmarksPage() {
  const { t, lang, label } = useApp();
  const { data, error, loading, reload } = useApi<Bench>("/api/benchmarks");
  const [form, setForm] = useState({ terrain: "rainforest" as Terrain, diameter_in: 16, length_km: 50, target_margin: 0.15 });
  const [est, setEst] = useState<Estimate | null>(null);
  const [busy, setBusy] = useState(false);
  const [terrain, setTerrain] = useState<"all" | Terrain>("all");
  const [open, setOpen] = useState<Terrain | null>(null);
  const router = useRouter();
  const points = useMemo(() => (data?.points ?? []).filter((x) => terrain === "all" || x.terrain === terrain), [data, terrain]);

  const scatter = useMemo<ChartOption>(() => {
    const pts_ = points;
    const shown = TERRAINS.filter((tr) => terrain === "all" || tr === terrain);
    return {
      grid: { left: 64, right: 20, top: 34, bottom: 44 },
      legend: { ...legendBase, data: shown.map((tr) => label("terrains", tr)) },
      tooltip: {
        ...tooltipBase, trigger: "item",
        formatter: (p: { data: { p: Point } }) => {
          const x = p.data.p;
          return `<b>${x.code}</b> ${x.name}<br/>${x.diameter_in}" × ${x.length_km} km · ${period(x.finish_period, lang)}<br/>${t("bm.per_inch")}: ${money(x.cost_per_inch_km_usd, lang, "USD", false)}<br/>${t("bm.per_km_label")}: ${money(x.cost_per_km_usd, lang)}<br/>${t("bm.margin_delta")}: ${pts(x.margin_delta_pts, lang)}`;
        },
      },
      xAxis: { type: "value", name: t("bm.x"), nameLocation: "middle", nameGap: 28, nameTextStyle: { color: C.muted, fontSize: 11 }, ...axisBase },
      yAxis: { type: "value", ...axisBase, axisLabel: { ...axisBase.axisLabel, formatter: (v: number) => num(v, lang) } },
      series: shown.map((tr) => ({
        name: label("terrains", tr), type: "scatter",
        data: pts_.filter((x) => x.terrain === tr).map((x) => ({ value: [x.length_km, x.cost_per_inch_km_usd], p: x, symbolSize: 8 + x.diameter_in * 0.6 })),
        itemStyle: { color: TERRAIN_COLOR[tr], borderColor: "#fff", borderWidth: 2, opacity: 0.9 },
        emphasis: { scale: 1.2 }, cursor: "pointer",
      })),
    };
  }, [points, terrain, lang, t, label]);

  const heat = useMemo<ChartOption>(() => {
    const ov = data?.activity_overrun ?? ({} as Bench["activity_overrun"]);
    const acts = ["MOV", "DDV", "ZAN", "TEN", "SOL", "END", "REV", "BAJ", "CRU", "PH", "RES", "IND"];
    const cells: [number, number, number | null][] = [];
    acts.forEach((a, yi) => TERRAINS.forEach((tr, xi) => cells.push([xi, yi, ov[tr]?.[a] ?? null])));
    return {
      grid: { left: 170, right: 24, top: 10, bottom: 60 },
      tooltip: { ...tooltipBase, formatter: (p: { value: [number, number, number | null] }) => `${label("activities", acts[p.value[1]])} · ${label("terrains", TERRAINS[p.value[0]])}<br/><b>${p.value[2] === null ? "–" : pct(p.value[2], lang)}</b>` },
      xAxis: { type: "category", data: TERRAINS.map((tr) => label("terrains", tr)), ...axisBase, splitLine: { show: false }, axisLabel: { color: C.ink2, fontSize: 12 } },
      yAxis: { type: "category", data: acts.map((a) => label("activities", a)), inverse: true, ...axisBase, splitLine: { show: false }, axisLabel: { color: C.ink2, fontSize: 11.5 } },
      visualMap: {
        min: -0.3, max: 0.3, calculable: false, orient: "horizontal", left: "center", bottom: 0, itemWidth: 10, itemHeight: 140,
        inRange: { color: [C.blue550, C.blue300, C.divNeutral, "#f3a3a2", C.red] },
        text: ["+30%", "−30%"], textStyle: { color: C.muted, fontSize: 11 },
      },
      series: [{
        type: "heatmap", data: cells, itemStyle: { borderColor: "#fff", borderWidth: 2, borderRadius: 4 },
        label: { show: true, fontSize: 11, color: C.ink, formatter: (p: { value: [number, number, number | null] }) => (p.value[2] !== null && Math.abs(p.value[2]) >= 0.05 ? pct(p.value[2], lang, 0) : "") },
      }],
    };
  }, [data, lang, label]);

  async function estimate() {
    setBusy(true);
    try {
      setEst(await api<Estimate>("/api/benchmarks/estimate", { method: "POST", body: JSON.stringify(form) }));
    } finally {
      setBusy(false);
    }
  }

  if (error && !data) return <ErrorState message={error} onRetry={reload} />;
  if (loading || !data) return <Loading />;

  return (
    <>
      <PageHeader title={t("bm.title")} subtitle={t("bm.sub", { year: data.base_year, esc: pct(data.escalation, lang, 0) })}>
        <Select label={t("pf.f.terrain")} value={terrain} onChange={setTerrain}
          options={[{ value: "all", label: t("common.all") }, ...TERRAINS.map((tr) => ({ value: tr, label: label("terrains", tr) }))]} />
      </PageHeader>

      <div className="mb-6 grid gap-4 md:grid-cols-3">
        {TERRAINS.map((tr) => {
          const s = data.by_terrain[tr];
          if (!s) return null;
          return (
            <button key={tr} onClick={() => setOpen(tr)}
              className={clsx("group rounded-xl bg-white p-4 text-left ring-1 ring-black/[0.07] transition-shadow hover:shadow-md hover:ring-[#2a78d6]/40", terrain !== "all" && terrain !== tr && "opacity-50")}>
              <div className="flex items-center justify-between">
                <p className="flex items-center gap-2 text-[14px] font-semibold text-slate-900">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: TERRAIN_COLOR[tr] }} /> {label("terrains", tr)}
                </p>
                <Badge>{t("bm.n", { n: s.n })}</Badge>
              </div>
              <p className="mt-3 text-[12px] text-slate-500">{t("bm.per_inch")} ({t("bm.median")})</p>
              <p className="text-[24px] font-semibold tracking-tight text-slate-900">{money(s.cost_per_inch_km_p50, lang, "USD", false)}</p>
              <dl className="mt-2 grid grid-cols-2 gap-y-1 text-[12.5px]">
                <dt className="text-slate-500">{t("bm.per_km")}</dt><dd className="text-right font-medium">{money(s.cost_per_km_p50, lang)}</dd>
                <dt className="text-slate-500">{t("bm.overrun")}</dt><dd className={clsx("text-right font-medium", s.overrun_p50 > 0.03 && "text-red-700")}>{pct(s.overrun_p50, lang)}</dd>
                <dt className="text-slate-500">{t("bm.margin_delta")}</dt><dd className={clsx("text-right font-medium", s.margin_delta_p50 < -0.03 && "text-red-700")}>{pts(s.margin_delta_p50, lang)}</dd>
                <dt className="text-slate-500">{t("bm.delay")}</dt><dd className="text-right font-medium">{num(s.delay_p50, lang, 1)} {t("common.months")}</dd>
              </dl>
              <p className="mt-2 flex items-center gap-0.5 text-[11.5px] font-medium text-[#2a78d6] opacity-70 group-hover:opacity-100">{t("bm.see_projects")} <ChevronRight className="h-3 w-3" /></p>
            </button>
          );
        })}
      </div>

      <div className="mb-6 grid gap-6 xl:grid-cols-2">
        <Card title={t("bm.scatter")} subtitle={t("bm.click_dot")}>
          <Chart option={scatter} height={360} ariaLabel={t("bm.scatter")} onClick={(p) => { const c = (p as unknown as { data?: { p?: Point } }).data?.p?.code; if (c) router.push(`/projects/${c}`); }} />
        </Card>
        <Card title={t("bm.heatmap")} subtitle={t("bm.heat_hint")}><Chart option={heat} height={430} ariaLabel={t("bm.heatmap")} /></Card>
      </div>

      <Card title={<span className="flex items-center gap-2"><Calculator className="h-4 w-4" /> {t("bm.estimator")}</span>} subtitle={t("bm.est_sub")} className="mb-6">
        <div className="grid gap-6 lg:grid-cols-[340px_minmax(0,1fr)]">
          <div className="space-y-3">
            <div>
              <p className="mb-1 text-[12px] font-medium text-slate-500">{t("pj.terrain")}</p>
              <Segmented value={form.terrain} onChange={(v) => setForm({ ...form, terrain: v })} size="sm"
                options={TERRAINS.map((tr) => ({ value: tr, label: label("terrains", tr) }))} />
            </div>
            {([["diameter_in", "bm.diameter", 1], ["length_km", "bm.length", 1]] as const).map(([k, lbl, step]) => (
              <label key={k} className="block">
                <span className="mb-1 block text-[12px] font-medium text-slate-500">{t(lbl)}</span>
                <input type="number" step={step} value={form[k]} onChange={(e) => setForm({ ...form, [k]: Number(e.target.value) })}
                  className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-[14px] outline-none focus:border-[#2a78d6]" />
              </label>
            ))}
            <label className="block">
              <span className="mb-1 block text-[12px] font-medium text-slate-500">{t("bm.target")}: {pct(form.target_margin, lang, 0)}</span>
              <input type="range" min={0.05} max={0.3} step={0.01} value={form.target_margin} onChange={(e) => setForm({ ...form, target_margin: Number(e.target.value) })} className="w-full accent-[#132a45]" />
            </label>
            <button onClick={estimate} disabled={busy} className="inline-flex items-center gap-2 rounded-lg bg-[#132a45] px-4 py-2 text-[13px] font-medium text-white disabled:opacity-50">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Calculator className="h-4 w-4" />} {t("bm.estimate")}
            </button>
          </div>
          <div>
            {est ? (
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="rounded-xl bg-slate-50 p-4 ring-1 ring-slate-100">
                  <p className="text-[12px] text-slate-500">{t("bm.cost_range")}</p>
                  <p className="mt-1 text-[20px] font-semibold text-slate-900">{money(est.cost_p50, lang)}</p>
                  <p className="text-[12px] text-slate-500">{money(est.cost_p25, lang)} – {money(est.cost_p75, lang)}</p>
                </div>
                <div className="rounded-xl bg-slate-50 p-4 ring-1 ring-slate-100">
                  <p className="text-[12px] text-slate-500">{t("bm.contingency")}</p>
                  <p className="mt-1 text-[20px] font-semibold text-amber-700">+{pct(est.contingency_pct, lang)}</p>
                  <p className="text-[12px] text-slate-500">{t("bm.contingency_sub")}</p>
                </div>
                <div className="rounded-xl bg-[#132a45] p-4 text-white">
                  <p className="text-[12px] text-slate-300">{t("bm.price")}</p>
                  <p className="mt-1 text-[20px] font-semibold">{money(est.suggested_price, lang)}</p>
                  <p className="text-[12px] text-slate-300">{t("bm.per_km_short", { v: money(est.price_per_km, lang) })}</p>
                </div>
                <div className="sm:col-span-3 text-[13px] text-slate-600">
                  <p>{t("bm.warn", { delta: pts(est.historical_margin_delta, lang) })}</p>
                  <p className="mt-2 flex flex-wrap items-center gap-1.5">
                    <span className="text-slate-500">{t("bm.sample")}:</span>
                    {est.sample.map((c) => <Link key={c} href={`/projects/${c}`} className="rounded bg-white px-1.5 py-0.5 text-[12px] font-medium text-[#2a78d6] ring-1 ring-slate-200 hover:bg-blue-50">{c}</Link>)}
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex h-full min-h-[160px] items-center justify-center rounded-xl border border-dashed border-slate-300 text-[13px] text-slate-400">{t("bm.est_sub")}</div>
            )}
          </div>
        </div>
      </Card>

      <Card title={`${t("bm.table")} (${points.length})`} bodyClass="px-0 pb-2">
        <div className="overflow-x-auto">
          <table className="min-w-full text-[13px]">
            <thead className="border-y border-slate-100 bg-slate-50/60">
              <tr><Th>{t("pf.col.project")}</Th><Th>{t("pj.terrain")}</Th><Th>{t("bm.col.scope")}</Th><Th right>{t("bm.col.cost", { year: data.base_year })}</Th><Th right>{t("bm.col.per_km")}</Th><Th right>{t("bm.col.overrun")}</Th><Th>{t("bm.col.margin")}</Th></tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {points.map((x) => (
                <tr key={x.code} className="hover:bg-slate-50">
                  <Td><Link href={`/projects/${x.code}`} className="font-semibold text-[#2a78d6] hover:underline">{x.code}</Link> <span className="text-slate-600">{x.name}</span>
                    {x.origin === "upload" && <Badge tone="violet" className="ml-1.5">{t("bm.imported")}</Badge>}</Td>
                  <Td><span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ background: TERRAIN_COLOR[x.terrain] }} />{label("terrains", x.terrain)}</span></Td>
                  <Td className="whitespace-nowrap">{t("bm.scope_v", { d: x.diameter_in, km: num(x.length_km, lang, 1) })}</Td>
                  <Td right>{money(x.final_cost_usd, lang)}</Td>
                  <Td right>{money(x.cost_per_km_usd, lang)}</Td>
                  <Td right className={clsx((x.overrun_pct ?? 0) > 0.03 && "text-red-700")}>{pct(x.overrun_pct, lang)}</Td>
                  <Td className="whitespace-nowrap"><span className="text-slate-400">{pct(x.bid_margin_pct, lang)}</span> → <span className={clsx("font-semibold", x.margin_delta_pts < -0.03 ? "text-red-700" : x.margin_delta_pts > 0 ? "text-emerald-700" : "")}>{pct(x.final_margin_pct, lang)}</span></Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <DetailDrawer open={open !== null} onClose={() => setOpen(null)} title={open ? `${label("terrains", open)} · ${t("bm.n", { n: data.by_terrain[open]?.n ?? 0 })}` : ""} explain={t("bm.d.terrain")}>
        {open && (
          <table className="min-w-full text-[13px]">
            <thead className="border-b border-slate-200"><tr><Th>{t("pf.col.project")}</Th><Th right>{t("bm.per_inch_short")}</Th><Th right>{t("bm.col.overrun")}</Th><Th right>{t("bm.margin_delta")}</Th><Th right>{t("bm.d.delay")}</Th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {data.points.filter((x) => x.terrain === open).sort((a, b) => b.cost_per_inch_km_usd - a.cost_per_inch_km_usd).map((x) => (
                <tr key={x.code} className="cursor-pointer hover:bg-blue-50/40" onClick={() => router.push(`/projects/${x.code}`)}>
                  <Td><span className="font-semibold text-[#2a78d6]">{x.code}</span> <span className="text-slate-600">{x.name}</span>
                    <span className="block text-[11.5px] text-slate-400">{t("bm.scope_v", { d: x.diameter_in, km: num(x.length_km, lang, 1) })} · {period(x.finish_period, lang)}</span></Td>
                  <Td right>{money(x.cost_per_inch_km_usd, lang, "USD", false)}</Td>
                  <Td right className={clsx((x.overrun_pct ?? 0) > 0.03 && "text-red-700")}>{pct(x.overrun_pct, lang)}</Td>
                  <Td right className={clsx(x.margin_delta_pts < -0.03 && "text-red-700")}>{pts(x.margin_delta_pts, lang)}</Td>
                  <Td right>{num(x.delay_months, lang, 0)} {t("common.months")}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="mt-3 text-[12px] text-slate-400">{t("bm.d.median")}</p>
      </DetailDrawer>
    </>
  );
}
