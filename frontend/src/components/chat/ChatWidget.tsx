"use client";

import clsx from "clsx";
import { Maximize2, MessageCircle, RotateCcw, X } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useApi } from "@/lib/useApi";
import { useApp } from "../providers";
import ChatComposer from "./ChatComposer";
import { useChat } from "./ChatProvider";
import ChatThread, { BotAvatar } from "./ChatThread";

/** Welcome text and starter questions that fit the page the user is looking at. */
export function useChatIntro() {
  const { t, lang } = useApp();
  const path = usePathname();
  const { data: sugg } = useApi<{ suggestions: { id: string; text: string }[] }>(`/api/ask/suggestions?lang=${lang}`);
  const code = path.match(/^\/projects\/([A-Z]{2}-\d{4})/i)?.[1]?.toUpperCase();
  if (code) {
    return {
      welcome: `${t("chat.welcome")}\n\n${t("chat.welcome_project", { code })}`,
      starters: ["chat.q.status", "chat.q.margin", "chat.q.pending", "chat.q.anomalies"].map((k) => t(k, { code })),
    };
  }
  if (path.startsWith("/data")) {
    return { welcome: t("chat.welcome"), starters: [t("chat.q.quality"), t("chat.q.what"), t("chat.q.real"), t("chat.q.how")] };
  }
  if (path.startsWith("/bids")) {
    return { welcome: t("chat.welcome"), starters: [t("chat.q.bids"), t("chat.q.bids_source"), t("chat.q.benchmark"), t("chat.q.how")] };
  }
  if (path.startsWith("/connectors")) {
    return { welcome: t("chat.welcome"), starters: [t("chat.q.connectors"), t("chat.q.erp_change"), t("chat.q.bids_source"), t("chat.q.quality")] };
  }
  const base = (sugg?.suggestions ?? []).slice(0, 3).map((s) => s.text);
  return { welcome: t("chat.welcome"), starters: [...base, t("chat.q.how")] };
}

export default function ChatWidget() {
  const { t, health } = useApp();
  const { open, setOpen, reset, messages } = useChat();
  const path = usePathname();
  const router = useRouter();
  const intro = useChatIntro();

  // shareable link: ?assistant=open opens the chat on arrival
  useEffect(() => {
    const url = new URL(window.location.href);
    if (url.searchParams.get("assistant") === "open") {
      url.searchParams.delete("assistant");
      window.history.replaceState(null, "", url.pathname + url.search + url.hash);
      setOpen(true);
    }
  }, [setOpen]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setOpen]);

  if (path.startsWith("/ask")) return null; // the full-page chat is already on screen

  return (
    <>
      {open && (
        <section role="dialog" aria-label={t("chat.title")}
          className="fixed inset-0 z-40 flex flex-col bg-[#f5f6f8] sm:inset-auto sm:bottom-24 sm:right-5 sm:h-[min(640px,calc(100vh-8rem))] sm:w-[410px] sm:overflow-hidden sm:rounded-2xl sm:shadow-2xl sm:ring-1 sm:ring-black/10">
          <header className="flex items-center gap-3 bg-gradient-to-r from-[#132a45] to-[#1c5cab] px-4 py-3 text-white">
            <BotAvatar size="md" />
            <div className="min-w-0 flex-1">
              <p className="text-[14.5px] font-semibold leading-tight">{t("chat.title")}</p>
              <p className="flex items-center gap-1.5 text-[11.5px] text-sky-100">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                {health?.ai_enabled ? t("chat.online_ai") : t("chat.online_local")}
              </p>
            </div>
            {messages.length > 0 && (
              <button onClick={reset} title={t("chat.new")} aria-label={t("chat.new")} className="rounded-lg p-1.5 text-sky-100 hover:bg-white/10 hover:text-white">
                <RotateCcw className="h-4 w-4" />
              </button>
            )}
            <button onClick={() => { setOpen(false); router.push("/ask"); }} title={t("chat.expand")} aria-label={t("chat.expand")}
              className="rounded-lg p-1.5 text-sky-100 hover:bg-white/10 hover:text-white">
              <Maximize2 className="h-4 w-4" />
            </button>
            <button onClick={() => setOpen(false)} title={t("chat.close")} aria-label={t("chat.close")} className="rounded-lg p-1.5 text-sky-100 hover:bg-white/10 hover:text-white">
              <X className="h-5 w-5" />
            </button>
          </header>
          <div className="flex-1 overflow-y-auto px-3 py-4">
            <ChatThread welcome={intro.welcome} starters={intro.starters} compact />
          </div>
          <div className="border-t border-slate-200 bg-white p-2.5">
            <ChatComposer autoFocus compact />
          </div>
        </section>
      )}

      <button
        onClick={() => setOpen(!open)}
        aria-label={open ? t("chat.close") : t("chat.open")}
        className={clsx(
          "group fixed bottom-5 right-5 z-40 flex h-14 items-center gap-2 rounded-full bg-gradient-to-br from-[#132a45] to-[#2a78d6] pl-4 pr-4 text-white shadow-xl transition-all hover:shadow-2xl",
          open && "hidden sm:flex",
        )}
      >
        {open ? <X className="h-6 w-6" /> : <MessageCircle className="h-6 w-6" />}
        {!open && <span className="max-w-0 overflow-hidden whitespace-nowrap text-[14px] font-medium transition-all duration-300 group-hover:max-w-[220px] sm:max-w-[220px]">{t("chat.open")}</span>}
        {!open && messages.length === 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-3.5 w-3.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
            <span className="relative inline-flex h-3.5 w-3.5 rounded-full border-2 border-white bg-emerald-400" />
          </span>
        )}
      </button>
    </>
  );
}
