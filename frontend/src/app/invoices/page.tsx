"use client";

/**
 * Supplier invoices.
 *
 * The page is laid out in the order the discovery call asked for, so it can
 * be walked straight down in the meeting:
 *
 *   1. digital invoices *and* scanned paper — the channel strip;
 *   2. fields read and checked before anything is submitted — the queue and
 *      the working behind each invoice;
 *   3. posted into the accounting system without touching the external
 *      accountant's connection — the posting strip and the connector link;
 *   4. exceptions, with a person approving — the held list;
 *   5. time saved at the real volume — the estimator at the foot.
 */

import clsx from "clsx";
import {
  AlertTriangle, Camera, CheckCircle2, FileText, Globe, Mail, Printer, RefreshCw, Users,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { useApp } from "@/components/providers";
import {
  Badge, Card, DetailDrawer, ErrorState, Loading, PageHeader, Segmented, Stat, Td, Th, type Tone,
} from "@/components/ui";
import { api, type InvoiceDetail, type InvoiceRow, type InvoicesResp, type Projection, type Savings } from "@/lib/api";
import { date, num } from "@/lib/format";
import { invalidateAll, useApi } from "@/lib/useApi";

const CHANNEL_ICON = { email: Mail, scan: Printer, photo: Camera, portal: Globe } as const;
const STATUS_TONE: Record<InvoiceRow["status"], Tone> = {
  read: "neutral", checked: "blue", held: "amber", approved: "blue", posted: "green",
};

function pesos(x: number, currency = "ARS"): string {
  return new Intl.NumberFormat("es-AR", {
    style: "currency", currency, maximumFractionDigits: 0,
  }).format(x || 0);
}

export default function InvoicesPage() {
  const { t, lang } = useApp();
  const [status, setStatus] = useState<"all" | InvoiceRow["status"]>("all");
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState<number | null>(null);
  const [syncing, setSyncing] = useState(false);

  const { data, error, loading, reload } = useApi<InvoicesResp>(
    `/api/invoices?status=${status}&limit=400`,
  );
  const { data: saved } = useApi<Savings>("/api/invoices/savings");
  const { data: detail } = useApi<InvoiceDetail>(open ? `/api/invoices/${open}` : null);

  const rows = useMemo(() => {
    const all = data?.invoices ?? [];
    if (!search.trim()) return all;
    const needle = search.toLowerCase().trim();
    return all.filter(
      (r) =>
        r.vendor_name.toLowerCase().includes(needle) ||
        r.number.includes(needle) ||
        r.filename.toLowerCase().includes(needle),
    );
  }, [data, search]);

  const byChannel = useMemo(() => {
    const out: Record<string, number> = {};
    for (const r of data?.invoices ?? []) out[r.channel] = (out[r.channel] ?? 0) + 1;
    return out;
  }, [data]);

  async function syncNow() {
    setSyncing(true);
    try {
      await api("/api/connectors/bejerman/sync", { method: "POST" });
      invalidateAll();
      reload();
    } finally {
      setSyncing(false);
    }
  }

  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (loading && !data) return <Loading label={t("inv.loading")} />;

  const counts = data?.counts ?? {};
  const held = counts.held ?? 0;
  const posted = counts.posted ?? 0;
  const waiting = (counts.approved ?? 0) + (counts.read ?? 0) + (counts.checked ?? 0);

  return (
    <div className="space-y-5">
      <PageHeader title={t("inv.title")} subtitle={t("inv.sub")}>
        <button
          onClick={syncNow}
          disabled={syncing || waiting === 0}
          className="inline-flex items-center gap-2 rounded-lg bg-[#1c5cab] px-3 py-2 text-sm font-medium text-white
                     hover:bg-[#164a8a] disabled:opacity-40"
        >
          <RefreshCw className={clsx("h-4 w-4", syncing && "animate-spin")} />
          {t("inv.post_now", { n: waiting })}
        </button>
      </PageHeader>

      {/* 1 + 2 + 3 + 4 — what happened to the month's invoices */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label={t("inv.received")} value={num(data?.total ?? 0, lang)} sub={t("inv.received_sub")} />
        <Stat
          label={t("inv.posted")} value={num(posted, lang)} tone="green"
          sub={t("inv.posted_sub", { p: saved?.straight_through_pct ?? 0 })}
        />
        <Stat label={t("inv.held")} value={num(held, lang)} tone={held ? "amber" : undefined} sub={t("inv.held_sub")} />
        <Stat
          label={t("inv.hours")} value={`${num(saved?.hours_saved ?? 0, lang, 1)} h`}
          sub={t("inv.hours_sub", { m: saved?.minutes_each ?? 0 })}
        />
      </div>

      {/* 1 — digital and paper, side by side */}
      <Card title={t("inv.channels")} subtitle={t("inv.channels_sub")}>
        <div className="grid gap-3 sm:grid-cols-4">
          {(["email", "portal", "scan", "photo"] as const).map((channel) => {
            const Icon = CHANNEL_ICON[channel];
            const paper = channel === "scan" || channel === "photo";
            return (
              <div key={channel} className="flex items-center gap-3 rounded-lg border border-slate-200 p-3">
                <div className={clsx("rounded-lg p-2", paper ? "bg-amber-50 text-amber-700" : "bg-blue-50 text-[#1c5cab]")}>
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-lg font-semibold tabular-nums">{num(byChannel[channel] ?? 0, lang)}</div>
                  <div className="text-xs text-slate-500">{t(`inv.ch.${channel}`)}</div>
                </div>
              </div>
            );
          })}
        </div>
        <p className="mt-3 text-xs text-slate-500">{t("inv.channels_note")}</p>
      </Card>

      {/* 4 — the exceptions, by reason */}
      {Object.keys(data?.exceptions ?? {}).length > 0 && (
        <Card title={t("inv.exceptions")} subtitle={t("inv.exceptions_sub")}>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(data!.exceptions).sort((a, b) => b[1] - a[1]).map(([kind, n]) => {
              const sample = (data?.invoices ?? []).find((r) => r.exception_kind === kind);
              return (
                <button
                  key={kind}
                  onClick={() => { setStatus("held"); setSearch(""); }}
                  className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50/50 p-3 text-left hover:bg-amber-50"
                >
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-slate-800">
                      {n} · {t(`inv.ex.${kind}`)}
                    </div>
                    <div className="mt-0.5 text-xs text-slate-600">
                      {sample?.why?.[lang] ?? sample?.exception_detail}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </Card>
      )}

      {/* 2 — the queue, with the working behind each one */}
      <Card
        title={t("inv.queue")}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t("inv.search")}
              className="w-44 rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm"
            />
            <Segmented
              size="sm"
              value={status}
              onChange={setStatus}
              options={[
                { value: "all", label: `${t("common.all")} ${data?.total ?? 0}` },
                { value: "posted", label: `${t("inv.s.posted")} ${posted}` },
                { value: "held", label: `${t("inv.s.held")} ${held}` },
              ]}
            />
          </div>
        }
        bodyClass="p-0"
      >
        <div className="max-h-[32rem] overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 z-10 bg-slate-50">
              <tr>
                <Th>{t("inv.c.vendor")}</Th>
                <Th>{t("inv.c.doc")}</Th>
                <Th>{t("inv.c.date")}</Th>
                <Th right>{t("inv.c.total")}</Th>
                <Th>{t("inv.c.status")}</Th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={r.id}
                  onClick={() => setOpen(r.id)}
                  className="cursor-pointer border-t border-slate-100 hover:bg-slate-50"
                >
                  <Td>
                    <div className="font-medium text-slate-800">{r.vendor_name}</div>
                    <div className="text-xs text-slate-500">{r.vendor_tax_id}</div>
                  </Td>
                  <Td>
                    <div className="flex items-center gap-1.5">
                      <Badge tone={r.letter === "A" ? "blue" : "neutral"}>{r.letter}</Badge>
                      <span className="tabular-nums text-slate-700">{r.number}</span>
                    </div>
                    <div className="text-xs text-slate-500">{r.filename}</div>
                  </Td>
                  <Td>{date(r.invoice_date, lang)}</Td>
                  <Td right>
                    <span className="tabular-nums">{pesos(r.total, r.currency)}</span>
                    {r.perception > 0 && (
                      <div className="text-xs text-slate-500">{t("inv.with_perception")}</div>
                    )}
                  </Td>
                  <Td>
                    <Badge tone={STATUS_TONE[r.status]}>{t(`inv.s.${r.status}`)}</Badge>
                    {r.exception_kind && (
                      <div className="mt-0.5 text-xs text-amber-700">{t(`inv.ex.${r.exception_kind}`)}</div>
                    )}
                  </Td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr><Td className="py-8 text-center text-slate-500">{t("inv.none")}</Td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* 5 — what it is worth at the real volume */}
      <Estimator measured={saved} />

      {/* 3 — where it goes */}
      <Card title={t("inv.where")} subtitle={t("inv.where_sub")}>
        <Link
          href="/connectors"
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm
                     font-medium text-[#1c5cab] hover:bg-slate-50"
        >
          <CheckCircle2 className="h-4 w-4" />
          {t("inv.open_connector")}
        </Link>
        <p className="mt-3 text-xs text-slate-500">{t("inv.where_note")}</p>
      </Card>

      <InvoiceDrawer detail={detail} onClose={() => setOpen(null)} onChanged={() => { invalidateAll(); reload(); }} />
    </div>
  );
}

/* --------------------------------------------------------------- estimator */

function Estimator({ measured }: { measured: Savings | null }) {
  const { t, lang } = useApp();
  const [perMonth, setPerMonth] = useState(420);
  const [minutes, setMinutes] = useState(4.5);
  const [cost, setCost] = useState(0);
  const [out, setOut] = useState<Projection | null>(null);
  const [busy, setBusy] = useState(false);

  const share = measured?.straight_through_pct ?? 87.4;

  async function run() {
    setBusy(true);
    try {
      setOut(await api<Projection>("/api/invoices/projection", {
        method: "POST",
        body: JSON.stringify({
          invoices_per_month: perMonth, minutes_each: minutes,
          straight_through_pct: share, hourly_cost: cost,
        }),
      }));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title={t("inv.est")} subtitle={t("inv.est_sub", { p: share })}>
      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <div className="space-y-3">
          <Field label={t("inv.est.per_month")} value={perMonth} onChange={setPerMonth} min={0} max={5000} step={10} />
          <Field label={t("inv.est.minutes")} value={minutes} onChange={setMinutes} min={0.5} max={30} step={0.5} />
          <Field label={t("inv.est.cost")} value={cost} onChange={setCost} min={0} max={200} step={1} />
          <button
            onClick={run}
            disabled={busy}
            className="rounded-lg bg-[#1c5cab] px-3 py-2 text-sm font-medium text-white hover:bg-[#164a8a] disabled:opacity-40"
          >
            {t("inv.est.run")}
          </button>
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4">
          {out ? (
            <div className="space-y-3">
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-semibold tabular-nums text-slate-900">
                  {num(out.hours_per_month, lang, 1)}
                </span>
                <span className="text-sm text-slate-600">{t("inv.est.hours_month")}</span>
              </div>
              <dl className="grid grid-cols-2 gap-2 text-sm">
                <Line k={t("inv.est.per_year")} v={`${num(out.hours_per_year, lang)} h`} />
                <Line k={t("inv.est.days")} v={num(out.days_per_month, lang, 1)} />
                <Line k={t("inv.est.mornings")} v={num(out.mornings_per_week, lang, 1)} />
                {out.cost_per_year !== null && out.cost_per_year > 0 && (
                  <Line k={t("inv.est.money")} v={`USD ${num(out.cost_per_year, lang)}`} />
                )}
              </dl>
              <p className="pt-2 text-xs text-slate-500">{t("inv.est.note")}</p>
            </div>
          ) : (
            <div className="flex h-full items-center justify-center text-center text-sm text-slate-500">
              {t("inv.est.empty")}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

function Field({ label, value, onChange, min, max, step }: {
  label: string; value: number; onChange: (n: number) => void; min: number; max: number; step: number;
}) {
  return (
    <label className="block">
      <div className="mb-1 flex items-baseline justify-between">
        <span className="text-sm text-slate-700">{label}</span>
        <input
          type="number"
          value={value}
          min={min}
          max={max}
          step={step}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-24 rounded border border-slate-300 px-2 py-1 text-right text-sm tabular-nums"
        />
      </div>
      <input
        type="range"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-[#1c5cab]"
      />
    </label>
  );
}

function Line({ k, v }: { k: string; v: string }) {
  return (
    <>
      <dt className="text-slate-600">{k}</dt>
      <dd className="text-right font-medium tabular-nums text-slate-900">{v}</dd>
    </>
  );
}

/* ------------------------------------------------------------------ drawer */

function InvoiceDrawer({ detail, onClose, onChanged }: {
  detail: InvoiceDetail | null; onClose: () => void; onChanged: () => void;
}) {
  const { t, lang } = useApp();
  const [busy, setBusy] = useState(false);

  async function approve() {
    if (!detail) return;
    setBusy(true);
    try {
      await api(`/api/invoices/${detail.id}/approve`, {
        method: "POST",
        body: JSON.stringify({ by: "Nicolás Varela" }),
      });
      onChanged();
      onClose();
    } finally {
      setBusy(false);
    }
  }

  return (
    <DetailDrawer
      open={Boolean(detail)}
      onClose={onClose}
      title={detail ? `${detail.document_type_name} ${detail.number}` : ""}
      explain={detail ? t("inv.drawer_explain") : undefined}
    >
      {detail && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-2 text-sm">
            <Line k={t("inv.c.vendor")} v={detail.vendor_name} />
            <Line k="CUIT" v={detail.vendor_tax_id} />
            <Line k={t("inv.c.date")} v={date(detail.invoice_date, lang) || "—"} />
            <Line k="CAE" v={detail.authorisation_code || "—"} />
            <Line k={t("inv.vto")} v={date(detail.authorisation_expires, lang) || "—"} />
            <Line k={t("inv.channel")} v={t(`inv.ch.${detail.channel}`)} />
          </div>

          <div className="rounded-lg border border-slate-200 p-3">
            <dl className="grid grid-cols-2 gap-1.5 text-sm">
              <Line k={t("inv.net")} v={pesos(detail.net, detail.currency)} />
              <Line k="IVA" v={detail.vat ? pesos(detail.vat, detail.currency) : t("inv.no_vat")} />
              {detail.perception > 0 && (
                <Line k={t("inv.perception")} v={pesos(detail.perception, detail.currency)} />
              )}
              <Line k={t("inv.total")} v={pesos(detail.total, detail.currency)} />
            </dl>
          </div>

          <div>
            <div className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
              {t("inv.checks")}
            </div>
            <ul className="space-y-1.5">
              {detail.checks.map((c, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  {c.ok ? (
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                  ) : (
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                  )}
                  <span className={clsx("min-w-0", c.ok ? "text-slate-700" : "text-amber-800")}>
                    <span className="font-medium">{c.name}</span>
                    <span className="text-slate-500"> — {c.detail}</span>
                  </span>
                </li>
              ))}
            </ul>
            {detail.notes.length > 0 && (
              <ul className="mt-2 space-y-1 text-xs text-slate-500">
                {detail.notes.map((n, i) => <li key={i}>{n}</li>)}
              </ul>
            )}
          </div>

          {detail.posted_reference ? (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50/60 p-3 text-sm">
              <div className="font-medium text-emerald-900">{t("inv.posted_in")}</div>
              <div className="mt-1 tabular-nums text-emerald-800">{detail.posted_reference}</div>
              <div className="mt-1 text-xs text-emerald-700">
                {t(`inv.route.${detail.posted_route ?? "screen"}`)} · {detail.approved_by}
              </div>
            </div>
          ) : detail.status === "held" ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50/60 p-3">
              <div className="flex items-start gap-2 text-sm">
                <Users className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
                <div>
                  <div className="font-medium text-amber-900">{t("inv.needs_person")}</div>
                  <div className="mt-0.5 text-amber-800">{detail.why?.[lang] ?? detail.exception_detail}</div>
                </div>
              </div>
              <button
                onClick={approve}
                disabled={busy}
                className="mt-3 rounded-lg bg-amber-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-40"
              >
                {t("inv.approve")}
              </button>
              <p className="mt-2 text-xs text-amber-700">{t("inv.approve_note")}</p>
            </div>
          ) : (
            <div className="rounded-lg border border-blue-200 bg-blue-50/60 p-3 text-sm text-blue-900">
              {t("inv.waiting_post")}
            </div>
          )}

          <div className="flex items-center gap-2 text-xs text-slate-500">
            <FileText className="h-3.5 w-3.5" />
            {detail.document?.filename ?? detail.filename}
          </div>
        </div>
      )}
    </DetailDrawer>
  );
}
