"use client";

/**
 * The front door, built around the two things Montamar actually asked for.
 *
 * The discovery call named one confirmed pain and one possible one:
 *
 *   1. an employee spends every morning typing supplier invoices into the
 *      accounting system;
 *   2. technical data arrives through cloud platforms, email attachments,
 *      shared folders and geospatial files, and nobody can see it in one
 *      place.
 *
 * So this page answers those two and nothing else. The margin dashboards,
 * bid comparisons and cost-per-kilometre benchmarks that used to live here
 * are about *building* pipelines. Montamar protects them. Leaving them on
 * the front page would have been showing a buyer somebody else's business,
 * which the call explicitly warned against.
 */

import clsx from "clsx";
import {
  AlertTriangle, ArrowRight, Camera, CheckCircle2, Clock, FileSpreadsheet, FileText, Globe,
  Landmark, Mail, Map, Printer, ShieldCheck, UploadCloud,
} from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";

import { useApp } from "@/components/providers";
import { Card, ErrorState, Loading, Stat } from "@/components/ui";
import type { Datahub, InvoicesResp, Savings } from "@/lib/api";
import { num } from "@/lib/format";
import { useApi } from "@/lib/useApi";

const CHANNEL_ICON = { email: Mail, scan: Printer, photo: Camera, portal: Globe } as const;

export default function Home() {
  const { t, lang } = useApp();
  const { data: inv, error, loading, reload } = useApi<InvoicesResp>("/api/invoices?limit=400");
  const { data: saved } = useApi<Savings>("/api/invoices/savings");
  const { data: hub } = useApi<Datahub>("/api/datahub");

  const byChannel = useMemo(() => {
    const out: Record<string, number> = {};
    for (const r of inv?.invoices ?? []) out[r.channel] = (out[r.channel] ?? 0) + 1;
    return out;
  }, [inv]);

  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (loading && !inv) return <Loading label={t("home.loading")} />;

  const posted = inv?.counts.posted ?? 0;
  const held = inv?.counts.held ?? 0;
  const paper = (byChannel.scan ?? 0) + (byChannel.photo ?? 0);

  return (
    <div className="space-y-6">
      {/* ---------------------------------------------------- the headline */}
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">{t("home.title")}</h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-600">{t("home.sub")}</p>
      </div>

      {/* ------------------------------------------- 1. the morning back */}
      <section>
        <div className="mb-2 flex items-baseline gap-2">
          <span className="rounded bg-[#132a45] px-1.5 py-0.5 text-[11px] font-semibold text-white">1</span>
          <h2 className="text-base font-semibold text-slate-800">{t("home.one")}</h2>
        </div>

        <div className="grid gap-3 lg:grid-cols-[2fr_1fr]">
          <Card bodyClass="p-0">
            <div className="grid gap-px bg-slate-200 sm:grid-cols-3">
              <div className="bg-white p-4">
                <div className="text-3xl font-semibold tabular-nums text-slate-900">
                  {num(inv?.total ?? 0, lang)}
                </div>
                <div className="mt-0.5 text-sm text-slate-600">{t("home.arrived")}</div>
                <div className="mt-1 text-xs text-slate-500">{t("home.arrived_sub", { n: paper })}</div>
              </div>
              <div className="bg-white p-4">
                <div className="text-3xl font-semibold tabular-nums text-emerald-700">
                  {num(posted, lang)}
                </div>
                <div className="mt-0.5 text-sm text-slate-600">{t("home.posted")}</div>
                <div className="mt-1 text-xs text-slate-500">
                  {t("home.posted_sub", { p: saved?.straight_through_pct ?? 0 })}
                </div>
              </div>
              <div className="bg-white p-4">
                <div className={clsx("text-3xl font-semibold tabular-nums", held ? "text-amber-700" : "text-slate-900")}>
                  {num(held, lang)}
                </div>
                <div className="mt-0.5 text-sm text-slate-600">{t("home.held")}</div>
                <div className="mt-1 text-xs text-slate-500">{t("home.held_sub")}</div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3 border-t border-slate-200 px-4 py-3">
              {(["email", "portal", "scan", "photo"] as const).map((c) => {
                const Icon = CHANNEL_ICON[c];
                const isPaper = c === "scan" || c === "photo";
                return (
                  <span
                    key={c}
                    className={clsx(
                      "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs",
                      isPaper ? "bg-amber-50 text-amber-800" : "bg-slate-100 text-slate-700",
                    )}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    <b className="tabular-nums">{byChannel[c] ?? 0}</b> {t(`inv.ch.${c}`)}
                  </span>
                );
              })}
            </div>
          </Card>

          {/* The number that answers "what is it worth". A plain element
              rather than a Card: Card sets bg-white in its own base class
              and that beat the dark background, which rendered the whole
              panel white on white. */}
          <div className="min-w-0 rounded-xl bg-[#132a45] p-5 text-white shadow-sm">
            <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-slate-300">
              <Clock className="h-3.5 w-3.5" /> {t("home.worth")}
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-4xl font-semibold tabular-nums">
                {num(saved?.hours_saved ?? 0, lang, 1)}
              </span>
              <span className="text-sm text-slate-300">{t("home.hours")}</span>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-slate-300">
              {t("home.worth_note", { m: saved?.minutes_each ?? 0 })}
            </p>
            <Link
              href="/invoices"
              className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-white/10 px-3 py-2 text-sm
                         font-medium text-white hover:bg-white/20"
            >
              {t("home.see_invoices")} <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>

        {held > 0 && (
          <Link
            href="/invoices"
            className="mt-3 flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50/60 p-3
                       text-sm hover:bg-amber-50"
          >
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
            <span className="text-slate-700">
              <b>{t("home.needs_you", { n: held })}</b> — {t("home.needs_you_sub")}
            </span>
          </Link>
        )}
      </section>

      {/* --------------------------------- 2. the data in one place */}
      <section>
        <div className="mb-2 flex items-baseline gap-2">
          <span className="rounded bg-[#132a45] px-1.5 py-0.5 text-[11px] font-semibold text-white">2</span>
          <h2 className="text-base font-semibold text-slate-800">{t("home.two")}</h2>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label={t("home.files")} value={num(hub?.files.total ?? 0, lang)} sub={t("home.files_sub")} />
          <Stat label={t("home.records")} value={num(hub?.records_total ?? 0, lang)} sub={t("home.records_sub")} />
          <Stat
            label={t("home.traced")} value={`${num((hub?.quality.lineage.rate ?? 1) * 100, lang)}%`}
            tone="green" sub={t("home.traced_sub")}
          />
          <Stat
            label={t("home.problems")} value={num(hub?.quality.erp_vs_excel.discrepancies?.length ?? 0, lang)}
            tone={(hub?.quality.erp_vs_excel.discrepancies?.length ?? 0) > 0 ? "amber" : undefined} sub={t("home.problems_sub")}
          />
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          <Route href="/ingest" icon={UploadCloud} title={t("home.r.load")} body={t("home.r.load_sub")} />
          <Route href="/data" icon={ShieldCheck} title={t("home.r.quality")} body={t("home.r.quality_sub")} />
          <Route href="/connectors" icon={Landmark} title={t("home.r.connect")} body={t("home.r.connect_sub")} />
        </div>
      </section>

      {/* ------------------------------------------------ what is not here */}
      <Card title={t("home.honest")} subtitle={t("home.honest_sub")}>
        <ul className="space-y-1.5 text-sm text-slate-600">
          {["bejerman", "volume", "shp", "synthetic"].map((k) => (
            <li key={k} className="flex items-start gap-2">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-slate-400" />
              <span>{t(`home.honest.${k}`)}</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

function Route({ href, icon: Icon, title, body }: {
  href: string; icon: typeof UploadCloud; title: string; body: string;
}) {
  return (
    <Link
      href={href}
      className="group flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-4 hover:border-[#1c5cab]/40 hover:shadow-sm"
    >
      <div className="rounded-lg bg-blue-50 p-2 text-[#1c5cab]"><Icon className="h-5 w-5" /></div>
      <div className="min-w-0">
        <div className="flex items-center gap-1 text-sm font-medium text-slate-800">
          {title}
          <ArrowRight className="h-3.5 w-3.5 opacity-0 transition-opacity group-hover:opacity-100" />
        </div>
        <p className="mt-0.5 text-xs leading-relaxed text-slate-500">{body}</p>
      </div>
    </Link>
  );
}
