"use client";

import clsx from "clsx";
import { AlertOctagon, AlertTriangle, ArrowRight, CheckCircle2, CircleDashed, Handshake, RefreshCw, Trophy, XCircle } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useApp } from "@/components/providers";
import { Badge, Card, DetailDrawer, ErrorState, Loading, PageHeader, Select, SourceLink, Stat, Td, Th, type Tone } from "@/components/ui";
import type { Bid, BidCheck, BidsResp } from "@/lib/api";
import { ago, money, num, pct, period, pts } from "@/lib/format";
import { useApi } from "@/lib/useApi";

type Risk = BidCheck["risk"];
const OPEN: Bid["stage"][] = ["prospecting", "preparing", "submitted", "negotiation"];
const RISK_TONE: Record<Risk, Tone> = { red: "red", amber: "amber", green: "green", none: "neutral" };
const RISK_ICON: Record<Risk, typeof AlertOctagon> = { red: AlertOctagon, amber: AlertTriangle, green: CheckCircle2, none: CircleDashed };
const RISK_ORDER: Record<Risk, number> = { red: 0, amber: 1, green: 2, none: 3 };

function RiskBadge({ risk }: { risk: Risk }) {
  const { t } = useApp();
  const Icon = RISK_ICON[risk];
  return <Badge tone={RISK_TONE[risk]}><Icon className="h-3 w-3" />{t(`bid.risk.${risk}`)}</Badge>;
}

function scope(b: Pick<Bid, "kind" | "diameter_in" | "length_km">, t: (k: string, p?: Record<string, string | number>) => string, lang: "es" | "en" | "pt") {
  return b.kind === "pipeline" && b.diameter_in && b.length_km ? t("bm.scope_v", { d: b.diameter_in, km: num(b.length_km, lang, 0) }) : t("kind.civil");
}

function BidDetail({ id }: { id: string }) {
  const { t, lang, country, label } = useApp();
  const router = useRouter();
  const { data: b, error } = useApi<Bid>(`/api/bids/${id}`);
  if (error) return <ErrorState message={error} />;
  if (!b) return <Loading />;
  const c = b.check;
  const verdict = c ? t(`bid.verdict.${c.risk}`, {
    left: pct(c.margin_left, lang), planned: pct(b.bid_margin_pct, lang), gap: pct(Math.abs(c.gap ?? 0), lang, 0),
  }) : null;
  return (
    <div className="space-y-5 text-[13px]">
      <div className="flex flex-wrap items-center gap-2 text-slate-600">
        <Badge tone="navy">{t(`bid.stage.${b.stage}`)}</Badge>
        <span>{b.client}</span>·<span>{country(b.country)} · {label("terrains", b.terrain)} · {b.region}</span>·<span>{scope(b, t, lang)}</span>
      </div>

      {c && (
        <div className={clsx("rounded-xl p-4 ring-1", c.risk === "red" ? "bg-red-50 ring-red-200" : c.risk === "amber" ? "bg-amber-50 ring-amber-200" : c.risk === "green" ? "bg-emerald-50 ring-emerald-200" : "bg-slate-50 ring-slate-200")}>
          <div className="flex items-center gap-2"><RiskBadge risk={c.risk} /></div>
          <p className="mt-2 text-[14px] leading-relaxed text-slate-800">{verdict}</p>
        </div>
      )}

      {c && c.risk !== "none" && (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-xl bg-white p-4 ring-1 ring-slate-200">
              <p className="text-[12px] font-semibold uppercase tracking-wide text-slate-400">{t("bid.d.bid_says")}</p>
              <dl className="mt-2 space-y-1.5">
                <div className="flex justify-between gap-3"><dt className="text-slate-500">{t("bid.d.value")}</dt><dd className="font-semibold text-slate-900">{money(b.value_usd, lang)}</dd></div>
                <div className="flex justify-between gap-3"><dt className="text-slate-500">{t("bid.d.planned_margin")}</dt><dd className="font-semibold text-slate-900">{pct(b.bid_margin_pct, lang)}</dd></div>
                <div className="flex justify-between gap-3"><dt className="text-slate-500">{t("bid.d.affordable")}</dt><dd className="font-semibold text-slate-900">{money(c.affordable_cost_usd, lang)}</dd></div>
              </dl>
            </div>
            <div className="rounded-xl bg-white p-4 ring-1 ring-slate-200">
              <p className="text-[12px] font-semibold uppercase tracking-wide text-slate-400">{t("bid.d.history_says")}</p>
              <dl className="mt-2 space-y-1.5">
                <div className="flex justify-between gap-3"><dt className="text-slate-500">{t("bid.d.history_cost")}</dt><dd className="font-semibold text-slate-900">{money(c.history_cost_usd, lang)}</dd></div>
                <div className="flex justify-between gap-3"><dt className="text-slate-500">{t("bid.d.margin_left")}</dt>
                  <dd className={clsx("font-semibold", c.risk === "red" ? "text-red-700" : c.risk === "amber" ? "text-amber-700" : "text-emerald-700")}>{pct(c.margin_left, lang)}</dd></div>
                <div className="flex justify-between gap-3"><dt className="text-slate-500">{t("bid.d.erosion")}</dt><dd className="font-semibold text-slate-900">{pts(c.typical_erosion ?? 0, lang)}</dd></div>
              </dl>
            </div>
          </div>
          {(c.price_gap_usd ?? 0) > 0 && (
            <p className="rounded-lg bg-blue-50 p-3 leading-relaxed text-slate-800">{t("bid.d.price_needed", { price: money(c.price_needed_usd, lang), diff: money(c.price_gap_usd, lang), margin: pct(b.bid_margin_pct, lang) })}</p>
          )}
          <p className="text-[12px] leading-relaxed text-slate-500">{t("bid.d.method", { low: money(c.history_low_usd, lang), high: money(c.history_high_usd, lang) })}</p>
        </>
      )}

      {!!b.comparables?.length && (
        <section>
          <p className="mb-1.5 font-semibold text-slate-900">{t("bid.d.comparables")}</p>
          <table className="min-w-full text-[12.5px]">
            <thead className="border-b border-slate-200"><tr><Th>{t("pf.col.project")}</Th><Th right>{t("bm.per_km_label")}</Th><Th right>{t("bm.margin_delta")}</Th><Th right>{t("bm.col.overrun")}</Th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {b.comparables.map((p) => (
                <tr key={p.code} className="cursor-pointer hover:bg-blue-50/40" onClick={() => router.push(`/projects/${p.code}`)}>
                  <Td><span className="font-semibold text-[#2a78d6]">{p.code}</span> <span className="text-slate-600">{p.name}</span>
                    <span className="block text-[11.5px] text-slate-400">{t("bm.scope_v", { d: p.diameter_in, km: num(p.length_km, lang, 0) })}</span></Td>
                  <Td right>{money(p.cost_per_km_usd, lang)}</Td>
                  <Td right className={clsx(p.margin_delta_pts < -0.03 && "text-red-700")}>{pts(p.margin_delta_pts, lang)}</Td>
                  <Td right>{pct(p.overrun_pct, lang)}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <section>
        <p className="mb-1.5 font-semibold text-slate-900">{t("bid.d.from_sales")}</p>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[12.5px]">
          <dt className="text-slate-500">{t("bid.col.value")}</dt><dd className="text-slate-800">{money(b.value, lang, b.currency, false)}</dd>
          <dt className="text-slate-500">{t("bid.d.probability")}</dt><dd className="text-slate-800">{pct(b.probability, lang, 0)}</dd>
          <dt className="text-slate-500">{t("bid.col.decision")}</dt><dd className="text-slate-800">{period(b.expected_decision, lang, true)}</dd>
          <dt className="text-slate-500">{t("bid.d.owner")}</dt><dd className="text-slate-800">{b.owner}</dd>
          <dt className="text-slate-500">{t("bid.d.next_step")}</dt><dd className="text-slate-800">{b.next_step[lang]}</dd>
          {b.project_code && <><dt className="text-slate-500">{t("pf.col.project")}</dt><dd><Link href={`/projects/${b.project_code}`} className="font-semibold text-[#2a78d6] hover:underline">{b.project_code}</Link></dd></>}
          {b.lost_reason && <><dt className="text-slate-500">{t("bid.d.lost_reason")}</dt><dd className="text-slate-800">{t(`bid.lost.${b.lost_reason}`)}</dd></>}
          <dt className="text-slate-500">{t("bid.d.modified")}</dt><dd className="text-slate-800">{b.modified_on}</dd>
        </dl>
        <SourceLink document_id={b.document_id} locator={b.locator} className="mt-3">{t("bid.d.source")}</SourceLink>
      </section>
    </div>
  );
}

export default function BidsPage() {
  const { t, lang, country, label } = useApp();
  const { data, error, loading, reload } = useApi<BidsResp>("/api/bids");
  const [ctry, setCtry] = useState<"all" | "EC" | "PE" | "BR">("all");
  const [stage, setStage] = useState<"all" | Bid["stage"]>("all");
  const [risk, setRisk] = useState<"all" | Risk>("all");
  const [open, setOpen] = useState<string | null>(null);
  const [panel, setPanel] = useState<null | "weighted" | "won">(null);

  const bids = useMemo(() => (data?.bids ?? []).filter((b) => ctry === "all" || b.country === ctry), [data, ctry]);
  const openBids = useMemo(() => bids
    .filter((b) => OPEN.includes(b.stage) && (stage === "all" || b.stage === stage) && (risk === "all" || b.check?.risk === risk))
    .sort((a, b) => RISK_ORDER[a.check!.risk] - RISK_ORDER[b.check!.risk] || b.value_usd - a.value_usd), [bids, stage, risk]);
  const k = useMemo(() => {
    const o = bids.filter((b) => OPEN.includes(b.stage));
    const sum = (xs: Bid[], f: (b: Bid) => number) => xs.reduce((a, b) => a + f(b), 0);
    const red = o.filter((b) => b.check?.risk === "red"), amber = o.filter((b) => b.check?.risk === "amber");
    const won = bids.filter((b) => b.stage === "won"), lost = bids.filter((b) => b.stage === "lost");
    return { open: o, openUsd: sum(o, (b) => b.value_usd), weighted: sum(o, (b) => b.weighted_usd), red, redUsd: sum(red, (b) => b.value_usd), amber, won, lost, wonUsd: sum(won, (b) => b.value_usd) };
  }, [bids]);

  if (error && !data) return <ErrorState message={error} onRetry={reload} />;
  if (loading || !data) return <Loading />;
  const filtered = ctry !== "all" || stage !== "all" || risk !== "all";
  const jump = () => document.getElementById("open-bids")?.scrollIntoView({ behavior: "smooth", block: "start" });

  return (
    <div className="space-y-6">
      <PageHeader title={t("bid.title")} subtitle={t("bid.sub")}>
        <div className="flex flex-wrap items-center gap-2">
          <Select label={t("pf.f.country")} value={ctry} onChange={setCtry} options={[
            { value: "all", label: t("common.all") }, { value: "EC", label: country("EC") }, { value: "PE", label: country("PE") }, { value: "BR", label: country("BR") }]} />
          <Select label={t("bid.f.stage")} value={stage} onChange={setStage} options={[
            { value: "all", label: t("common.all") }, ...OPEN.map((s) => ({ value: s, label: t(`bid.stage.${s}`) }))]} />
          <Select label={t("bid.f.risk")} value={risk} onChange={setRisk} options={[
            { value: "all", label: t("common.all") }, ...(["red", "amber", "green", "none"] as const).map((r) => ({ value: r, label: t(`bid.risk.${r}`) }))]} />
          {filtered && <button onClick={() => { setCtry("all"); setStage("all"); setRisk("all"); }} className="text-[12.5px] font-medium text-[#2a78d6] hover:underline">{t("pf.clear")}</button>}
        </div>
      </PageHeader>

      <Link href="/connectors" className="flex flex-wrap items-center gap-3 rounded-xl bg-white px-5 py-3 text-[13px] text-slate-600 ring-1 ring-black/[0.07] hover:ring-[#2a78d6]/40">
        <Handshake className="h-4 w-4 text-[#1c5cab]" />
        <span className="flex-1">{t("bid.source", { when: ago(data.last_sync?.at, lang) })}</span>
        <span className="inline-flex items-center gap-1 font-medium text-[#2a78d6]"><RefreshCw className="h-3.5 w-3.5" /> {t("bid.source_cta")}</span>
      </Link>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <Stat label={t("bid.kpi.open")} value={money(k.openUsd, lang)} sub={t("bid.kpi.open_sub", { n: k.open.length })} onClick={() => { setRisk("all"); jump(); }} />
        <Stat label={t("bid.kpi.weighted")} value={money(k.weighted, lang)} sub={t("bid.kpi.weighted_sub")} onClick={() => setPanel("weighted")} />
        <Stat label={t("bid.kpi.red")} value={k.red.length} tone={k.red.length ? "red" : undefined} sub={money(k.redUsd, lang)} onClick={() => { setRisk("red"); jump(); }} />
        <Stat label={t("bid.kpi.amber")} value={k.amber.length} tone={k.amber.length ? "amber" : undefined} sub={t("bid.kpi.amber_sub")} onClick={() => { setRisk("amber"); jump(); }} />
        <Stat label={t("bid.kpi.won")} value={k.won.length} sub={t("bid.kpi.won_sub", { v: money(k.wonUsd, lang), rate: pct(k.won.length / Math.max(k.won.length + k.lost.length, 1), lang, 0) })} onClick={() => setPanel("won")} />
      </div>

      <Card id="open-bids" title={`${t("bid.table")} (${openBids.length})`} subtitle={t("bid.table_sub")} bodyClass="px-0 pb-2">
        <div className="overflow-x-auto">
          <table className="min-w-full text-[13px]">
            <thead className="border-y border-slate-100 bg-slate-50/60">
              <tr>
                <Th>{t("bid.col.bid")}</Th><Th>{t("bid.col.stage")}</Th><Th right>{t("bid.col.value")}</Th>
                <Th right wrap>{t("bid.col.planned")}</Th><Th right wrap>{t("bid.col.left")}</Th><Th>{t("bid.col.check")}</Th><Th>{t("bid.col.decision")}</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {openBids.map((b) => {
                const c = b.check!;
                return (
                  <tr key={b.crm_id} onClick={() => setOpen(b.crm_id)} className="cursor-pointer hover:bg-slate-50">
                    <Td className="min-w-[260px]">
                      <p className="font-semibold text-slate-900">{b.name}</p>
                      <p className="text-[12px] text-slate-500">{b.crm_id} · {b.client}</p>
                      <p className="text-[12px] text-slate-400">{country(b.country)} · {label("terrains", b.terrain)} · {scope(b, t, lang)}</p>
                    </Td>
                    <Td><Badge tone={b.stage === "negotiation" ? "violet" : b.stage === "submitted" ? "blue" : "neutral"}>{t(`bid.stage.${b.stage}`)}</Badge></Td>
                    <Td right className="whitespace-nowrap">
                      <span className="font-medium text-slate-900">{money(b.value_usd, lang)}</span>
                      {b.currency !== "USD" && <span className="block text-[11.5px] text-slate-400">{money(b.value, lang, b.currency)}</span>}
                    </Td>
                    <Td right>{pct(b.bid_margin_pct, lang)}</Td>
                    <Td right className={clsx("font-semibold", c.risk === "red" ? "text-red-700" : c.risk === "amber" ? "text-amber-700" : c.risk === "green" ? "text-emerald-700" : "text-slate-300")}>
                      {c.risk === "none" ? "–" : pct(c.margin_left, lang)}
                    </Td>
                    <Td><RiskBadge risk={c.risk} /></Td>
                    <Td className="whitespace-nowrap text-slate-600">{period(b.expected_decision, lang)}</Td>
                  </tr>
                );
              })}
              {!openBids.length && <tr><Td className="py-8 text-center text-slate-400">{t("bid.empty")}</Td></tr>}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title={<span className="flex items-center gap-2"><Trophy className="h-4 w-4 text-emerald-600" /> {t("bid.won")} ({k.won.length})</span>} subtitle={t("bid.won_sub")} bodyClass="px-0 pb-2">
          <ul className="divide-y divide-slate-100">
            {k.won.map((b) => (
              <li key={b.crm_id} className="flex items-center justify-between gap-3 px-5 py-2.5 text-[13px]">
                <button onClick={() => setOpen(b.crm_id)} className="min-w-0 text-left">
                  <p className="truncate font-medium text-slate-900">{b.name}</p>
                  <p className="text-[12px] text-slate-500">{b.crm_id} · {period(b.expected_decision, lang)} · {money(b.value_usd, lang)}</p>
                </button>
                <Link href={`/projects/${b.project_code}`} className="inline-flex shrink-0 items-center gap-1 font-semibold text-[#2a78d6] hover:underline">{b.project_code} <ArrowRight className="h-3.5 w-3.5" /></Link>
              </li>
            ))}
          </ul>
        </Card>
        <Card title={<span className="flex items-center gap-2"><XCircle className="h-4 w-4 text-slate-400" /> {t("bid.lost")} ({k.lost.length})</span>} subtitle={t("bid.lost_sub")} bodyClass="px-0 pb-2">
          <ul className="divide-y divide-slate-100">
            {k.lost.map((b) => (
              <li key={b.crm_id}>
                <button onClick={() => setOpen(b.crm_id)} className="w-full px-5 py-2.5 text-left text-[13px] hover:bg-slate-50">
                  <p className="font-medium text-slate-900">{b.name}</p>
                  <p className="text-[12px] text-slate-500">{b.crm_id} · {period(b.expected_decision, lang)} · {money(b.value_usd, lang)} · <span className="text-slate-700">{t(`bid.lost.${b.lost_reason}`)}</span></p>
                  <p className="text-[12px] text-slate-400">{b.next_step[lang]}</p>
                </button>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <DetailDrawer open={!!open} onClose={() => setOpen(null)} title={open ? `${open} · ${data.bids.find((b) => b.crm_id === open)?.name ?? ""}` : ""}>
        {open && <BidDetail key={open} id={open} />}
      </DetailDrawer>

      <DetailDrawer open={panel === "weighted"} onClose={() => setPanel(null)} title={t("bid.kpi.weighted")} explain={t("bid.d.weighted")}>
        <table className="min-w-full text-[13px]">
          <thead className="border-b border-slate-200"><tr><Th>{t("bid.col.bid")}</Th><Th>{t("bid.col.stage")}</Th><Th right>{t("bid.col.value")}</Th><Th right>{t("bid.d.probability")}</Th><Th right>{t("bid.d.weighted_col")}</Th></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {k.open.map((b) => (
              <tr key={b.crm_id}><Td>{b.name}</Td><Td>{t(`bid.stage.${b.stage}`)}</Td><Td right>{money(b.value_usd, lang)}</Td><Td right>{pct(b.probability, lang, 0)}</Td><Td right className="font-semibold">{money(b.weighted_usd, lang)}</Td></tr>
            ))}
            <tr className="bg-slate-50 font-semibold"><Td>{t("pj.col.total")}</Td><Td /><Td right>{money(k.openUsd, lang)}</Td><Td /><Td right>{money(k.weighted, lang)}</Td></tr>
          </tbody>
        </table>
      </DetailDrawer>

      <DetailDrawer open={panel === "won"} onClose={() => setPanel(null)} title={t("bid.kpi.won")} explain={t("bid.d.won")}>
        <table className="min-w-full text-[13px]">
          <thead className="border-b border-slate-200"><tr><Th>{t("bid.col.bid")}</Th><Th right>{t("bid.col.value")}</Th><Th right>{t("bid.col.planned")}</Th><Th>{t("pf.col.project")}</Th></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {k.won.map((b) => (
              <tr key={b.crm_id}><Td>{b.name}<span className="block text-[11.5px] text-slate-400">{b.crm_id}</span></Td><Td right>{money(b.value_usd, lang)}</Td><Td right>{pct(b.bid_margin_pct, lang)}</Td>
                <Td><Link href={`/projects/${b.project_code}`} className="font-semibold text-[#2a78d6] hover:underline">{b.project_code}</Link></Td></tr>
            ))}
          </tbody>
        </table>
      </DetailDrawer>
    </div>
  );
}
