"use client";

import clsx from "clsx";
import { BarChart3, Cpu, Database, Handshake, LayoutDashboard, MessageSquareText, Plug, RotateCcw, ShieldCheck, Sparkles, UploadCloud, Workflow } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { api, API_URL, Lang } from "@/lib/api";
import { period } from "@/lib/format";
import { invalidateAll } from "@/lib/useApi";
import { useApp } from "./providers";
import ChatWidget from "./chat/ChatWidget";
import SourceDrawer from "./SourceDrawer";
import { Segmented } from "./ui";

const NAV = [
  { href: "/", key: "nav.portfolio", icon: LayoutDashboard },
  { href: "/bids", key: "nav.bids", icon: Handshake },
  { href: "/data", key: "nav.data", icon: ShieldCheck },
  { href: "/connectors", key: "nav.connectors", icon: Plug },
  { href: "/ingest", key: "nav.ingest", icon: UploadCloud },
  { href: "/ask", key: "nav.ask", icon: MessageSquareText },
  { href: "/benchmarks", key: "nav.benchmarks", icon: BarChart3 },
  { href: "/method", key: "nav.method", icon: Workflow },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const { t, lang, setLang, health, apiError, meta } = useApp();
  const path = usePathname();
  const [resetting, setResetting] = useState(false);

  const active = (href: string) => (href === "/" ? path === "/" || path.startsWith("/projects") : path.startsWith(href));

  async function reset() {
    if (!confirm(t("shell.reset_confirm"))) return;
    setResetting(true);
    try {
      await api("/api/admin/reset", { method: "POST" });
      invalidateAll();
    } finally {
      setResetting(false);
    }
  }

  return (
    <div className="flex min-h-screen bg-[#f5f6f8]">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col bg-[#132a45] text-slate-200 lg:flex">
        <div className="px-5 pb-6 pt-6">
          <p className="text-[17px] font-bold tracking-[0.18em] text-white">CONDUTO</p>
          <p className="mt-0.5 text-[12px] text-slate-400">{t("app.subtitle")}</p>
        </div>
        <nav className="flex-1 space-y-0.5 px-3">
          {NAV.map(({ href, key, icon: Icon }) => (
            <Link key={href} href={href} className={clsx(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-[13.5px] font-medium transition-colors",
              active(href) ? "bg-white/10 text-white" : "text-slate-300 hover:bg-white/5 hover:text-white",
            )}>
              <Icon className="h-4 w-4" /> {t(key)}
            </Link>
          ))}
        </nav>
        <div className="space-y-2 border-t border-white/10 px-5 py-4 text-[12px]">
          <div className="flex items-center gap-2">
            {health?.ai_enabled ? <Sparkles className="h-3.5 w-3.5 text-emerald-400" /> : <Cpu className="h-3.5 w-3.5 text-emerald-400" />}
            <span>{health ? (health.ai_enabled ? t("shell.ai_on") : t("shell.local_engine")) : "…"}</span>
          </div>
          <div className="flex items-center gap-2 text-slate-400">
            <Database className="h-3.5 w-3.5" />
            <span>{health ? t("shell.docs", { p: health.projects, d: health.documents }) : "…"}</span>
          </div>
          <button onClick={reset} disabled={resetting} className="flex items-center gap-2 text-slate-400 hover:text-white disabled:opacity-50">
            <RotateCcw className={clsx("h-3.5 w-3.5", resetting && "animate-spin")} /> {t("shell.reset")}
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
          <div className="flex items-center justify-between gap-3 px-4 py-2.5 lg:px-8">
            <div className="flex items-center gap-3 lg:hidden">
              <span className="text-[15px] font-bold tracking-[0.15em] text-[#132a45]">CONDUTO</span>
            </div>
            <div className="hidden items-center gap-2 text-[12px] text-slate-500 lg:flex">
              <span className="rounded-md bg-amber-50 px-2 py-0.5 font-medium text-amber-800 ring-1 ring-amber-200">{t("shell.synthetic")}</span>
              {meta && <span>{t("shell.cutoff")}: <b className="font-semibold text-slate-700">{period(meta.status_period, lang, true)}</b></span>}
            </div>
            <Segmented<Lang>
              size="sm"
              value={lang}
              onChange={setLang}
              options={[{ value: "es", label: "ES" }, { value: "en", label: "EN" }, { value: "pt", label: "PT" }]}
            />
          </div>
          <nav className="flex gap-1 overflow-x-auto px-3 pb-2 lg:hidden">
            {NAV.map(({ href, key, icon: Icon }) => (
              <Link key={href} href={href} className={clsx(
                "flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[13px] font-medium",
                active(href) ? "bg-[#132a45] text-white" : "text-slate-600 hover:bg-slate-100",
              )}>
                <Icon className="h-3.5 w-3.5" /> {t(key)}
              </Link>
            ))}
          </nav>
        </header>
        {apiError === "network" && (
          <div className="border-b border-red-200 bg-red-50 px-8 py-2 text-[13px] text-red-800">
            {t("shell.api_down")}: <code className="font-mono">{API_URL}</code>
          </div>
        )}
        <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 lg:px-8 lg:py-8">{children}</main>
      </div>
      <ChatWidget />
      <SourceDrawer />
    </div>
  );
}
