"use client";

import clsx from "clsx";
import { AlertOctagon, AlertTriangle, CheckCircle2, ChevronRight, FileSearch, Loader2, X } from "lucide-react";
import { useEffect, useState } from "react";
import type { Health } from "@/lib/api";
import { useApp } from "./providers";

export function Card({ title, subtitle, actions, children, className, bodyClass, id }: {
  title?: React.ReactNode; subtitle?: React.ReactNode; actions?: React.ReactNode; children: React.ReactNode; className?: string; bodyClass?: string; id?: string;
}) {
  return (
    <section id={id} className={clsx("min-w-0 scroll-mt-20 rounded-xl bg-white ring-1 ring-black/[0.07] shadow-[0_1px_2px_rgba(0,0,0,0.03)]", className)}>
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-3 px-5 pt-4">
          <div className="min-w-0">
            {title && <h2 className="text-[15px] font-semibold text-slate-900">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-[13px] text-slate-500">{subtitle}</p>}
          </div>
          {actions}
        </header>
      )}
      <div className={clsx("px-5 pb-5", title || actions ? "pt-3" : "pt-5", bodyClass)}>{children}</div>
    </section>
  );
}

export function PageHeader({ title, subtitle, children }: { title: React.ReactNode; subtitle?: React.ReactNode; children?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
        {subtitle && <p className="mt-1 max-w-3xl text-sm text-slate-500">{subtitle}</p>}
      </div>
      {children && <div className="ml-auto">{children}</div>}
    </div>
  );
}

const TONES = {
  neutral: "bg-slate-100 text-slate-700 ring-slate-200",
  blue: "bg-blue-50 text-blue-800 ring-blue-200",
  red: "bg-red-50 text-red-800 ring-red-200",
  amber: "bg-amber-50 text-amber-800 ring-amber-200",
  green: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  violet: "bg-violet-50 text-violet-800 ring-violet-200",
  navy: "bg-[#1f3a5f] text-white ring-[#1f3a5f]",
};
export type Tone = keyof typeof TONES;

export function Badge({ tone = "neutral", children, className, title }: { tone?: Tone; children: React.ReactNode; className?: string; title?: string }) {
  return (
    <span title={title} className={clsx("inline-flex items-center gap-1 whitespace-nowrap rounded-md px-1.5 py-0.5 text-[11px] font-medium ring-1 ring-inset", TONES[tone], className)}>
      {children}
    </span>
  );
}

export function HealthBadge({ health }: { health: Health }) {
  const { t } = useApp();
  const Icon = health === "red" ? AlertOctagon : health === "amber" ? AlertTriangle : CheckCircle2;
  const tone: Tone = health === "red" ? "red" : health === "amber" ? "amber" : "green";
  return (
    <Badge tone={tone}>
      <Icon className="h-3 w-3" aria-hidden />
      {t(`health.${health}`)}
    </Badge>
  );
}

const FLAG_TONE: Record<string, Tone> = {
  COST_OVERRUN: "red", MARGIN_EROSION: "red", SCHEDULE_DELAY: "amber", PENDING_CO: "violet", PENDING_CO_AGING: "violet", WELD_QUALITY: "amber",
};

export function Flags({ flags, max = 3 }: { flags: string[]; max?: number }) {
  const { t } = useApp();
  if (!flags.length) return <span className="text-xs text-slate-400">—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {flags.slice(0, max).map((f) => <Badge key={f} tone={FLAG_TONE[f] ?? "neutral"}>{t(`flag.${f}`)}</Badge>)}
      {flags.length > max && <Badge>+{flags.length - max}</Badge>}
    </div>
  );
}

export function ProgressBar({ actual, planned, className }: { actual: number; planned?: number; className?: string }) {
  const behind = planned !== undefined && actual < planned - 0.02;
  return (
    <div className={clsx("relative h-1.5 w-full rounded-full bg-slate-100", className)}>
      <div className={clsx("absolute inset-y-0 left-0 rounded-full", behind ? "bg-amber-500" : "bg-[#2a78d6]")} style={{ width: `${Math.min(actual, 1) * 100}%` }} />
      {planned !== undefined && (
        <div className="absolute -top-1 h-3.5 w-0.5 rounded bg-slate-700" style={{ left: `calc(${Math.min(planned, 1) * 100}% - 1px)` }} />
      )}
    </div>
  );
}

export function Stat({ label, value, sub, tone, source, onClick, className }: {
  label: React.ReactNode; value: React.ReactNode; sub?: React.ReactNode; tone?: "red" | "amber" | "green";
  source?: { document_id: number | null; locator: string | null } | null; onClick?: () => void; className?: string;
}) {
  const { openSource, t } = useApp();
  const color = tone === "red" ? "text-red-700" : tone === "amber" ? "text-amber-700" : tone === "green" ? "text-emerald-700" : "text-slate-900";
  return (
    <div className={clsx("group rounded-xl bg-white p-4 ring-1 ring-black/[0.07]", onClick && "cursor-pointer transition-shadow hover:shadow-md hover:ring-[#2a78d6]/40", className)} onClick={onClick}
      role={onClick ? "button" : undefined} tabIndex={onClick ? 0 : undefined} onKeyDown={onClick ? (e) => { if (e.key === "Enter") onClick(); } : undefined}>
      <div className="flex items-start justify-between gap-2">
        <p className="text-[12px] font-medium text-slate-500">{label}</p>
        {source?.document_id && (
          <button
            type="button"
            title={t("common.source")}
            onClick={(e) => { e.stopPropagation(); openSource({ kind: "source", document_id: source.document_id!, locator: source.locator }); }}
            className="-m-1 rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-[#1f3a5f]"
          >
            <FileSearch className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
      <p className={clsx("mt-1 text-[22px] font-semibold leading-tight tracking-tight", color)}>{value}</p>
      {sub && <p className="mt-1 text-[12px] text-slate-500">{sub}</p>}
      {onClick && <p className="mt-2 flex items-center gap-0.5 text-[11.5px] font-medium text-[#2a78d6] opacity-70 group-hover:opacity-100">{t("common.details")} <ChevronRight className="h-3 w-3" /></p>}
    </div>
  );
}

export function SourceLink({ document_id, locator, children, className }: { document_id: number | null; locator: string | null; children?: React.ReactNode; className?: string }) {
  const { openSource, t } = useApp();
  if (!document_id) return null;
  return (
    <button
      type="button"
      onClick={(e) => { e.stopPropagation(); openSource({ kind: "source", document_id, locator }); }}
      className={clsx("inline-flex items-center gap-1 rounded text-[12px] font-medium text-[#2a78d6] hover:underline", className)}
    >
      <FileSearch className="h-3.5 w-3.5" />
      {children ?? t("common.source")}
    </button>
  );
}

export function Segmented<T extends string>({ options, value, onChange, size = "md" }: {
  options: { value: T; label: React.ReactNode }[]; value: T; onChange: (v: T) => void; size?: "sm" | "md";
}) {
  return (
    <div className="inline-flex rounded-lg bg-slate-100 p-0.5">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={clsx(
            "rounded-md font-medium transition-colors",
            size === "sm" ? "px-2 py-0.5 text-[12px]" : "px-3 py-1 text-[13px]",
            value === o.value ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-800",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Loading({ label }: { label?: string }) {
  const { t } = useApp();
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), 4000);
    return () => clearTimeout(timer);
  }, []);
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-sm text-slate-500">
      <span className="flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" /> {label ?? t("common.loading")}</span>
      {slow && <span className="max-w-md text-center text-[13px] text-slate-400">{t("common.waking")}</span>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const { t } = useApp();
  return (
    <div className="rounded-xl bg-red-50 p-5 text-sm text-red-800 ring-1 ring-red-200">
      <p className="font-medium">{t("common.error")}</p>
      <p className="mt-1 text-red-700">{message === "network" ? t("shell.api_down") : message}</p>
      {onRetry && <button onClick={onRetry} className="mt-3 rounded-md bg-white px-3 py-1 text-xs font-medium ring-1 ring-red-200 hover:bg-red-100">{t("common.retry")}</button>}
    </div>
  );
}

export function Th({ children, className, right, wrap }: { children?: React.ReactNode; className?: string; right?: boolean; wrap?: boolean }) {
  return <th className={clsx(wrap ? "min-w-[90px] whitespace-normal" : "whitespace-nowrap", "px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500", right ? "text-right" : "text-left", className)}>{children}</th>;
}

export function Td({ children, className, right }: { children?: React.ReactNode; className?: string; right?: boolean }) {
  return <td className={clsx("px-3 py-2.5 align-middle", right && "text-right tabular-nums", className)}>{children}</td>;
}

/** Right-side panel that shows the data behind a number, with a plain explanation. */
export function DetailDrawer({ open, onClose, title, explain, children }: {
  open: boolean; onClose: () => void; title: React.ReactNode; explain?: React.ReactNode; children: React.ReactNode;
}) {
  const { t } = useApp();
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-slate-900/20" onClick={onClose} />
      <aside className="relative flex h-full w-full max-w-[720px] flex-col bg-white shadow-2xl">
        <header className="flex items-start justify-between gap-3 border-b border-slate-200 px-5 py-4">
          <div className="min-w-0">
            <p className="text-[16px] font-semibold text-slate-900">{title}</p>
            {explain && <p className="mt-1 text-[13px] leading-relaxed text-slate-500">{explain}</p>}
          </div>
          <button onClick={onClose} className="rounded p-1 text-slate-500 hover:bg-slate-100" aria-label={t("common.close")}><X className="h-5 w-5" /></button>
        </header>
        <div className="flex-1 overflow-y-auto p-5">{children}</div>
      </aside>
    </div>
  );
}

export function Select<T extends string>({ label, value, onChange, options }: {
  label: string; value: T; onChange: (v: T) => void; options: { value: T; label: string }[];
}) {
  return (
    <label className="flex items-center gap-1.5 rounded-lg bg-white px-2.5 py-1.5 text-[12.5px] ring-1 ring-slate-200 focus-within:ring-[#2a78d6]">
      <span className="text-slate-400">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value as T)} className="bg-transparent font-medium text-slate-800 outline-none">
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
}
