"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, useSyncExternalStore } from "react";
import type { Health_, Lang, Meta } from "@/lib/api";
import { translate } from "@/lib/i18n";
import { useApi } from "@/lib/useApi";

export type SourceRequest =
  | { kind: "source"; document_id: number; locator: string | null }
  | { kind: "activity"; project: string; activity: string };

type LabelGroup = "activities" | "terrains" | "issue_categories" | "co_causes" | "co_status" | "cost_types";

interface AppContext {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
  label: (group: LabelGroup, code: string | null | undefined) => string;
  country: (code: string) => string;
  meta: Meta | null;
  health: Health_ | null;
  apiError: string | null;
  source: SourceRequest | null;
  openSource: (req: SourceRequest) => void;
  closeSource: () => void;
}

const Ctx = createContext<AppContext | null>(null);

// Language lives in localStorage; useSyncExternalStore keeps SSR ("es") and the client in sync.
const LANG_KEY = "conduto.lang";
const langListeners = new Set<() => void>();
let memoryLang: Lang | null = null;

function readLang(): Lang {
  try {
    const saved = localStorage.getItem(LANG_KEY);
    if (saved === "es" || saved === "en" || saved === "pt") return saved;
  } catch {
    /* storage unavailable */
  }
  if (memoryLang) return memoryLang;
  const nav = (typeof navigator !== "undefined" && navigator.language ? navigator.language : "es").slice(0, 2).toLowerCase();
  return nav === "pt" ? "pt" : nav === "en" ? "en" : "es";
}

function subscribeLang(cb: () => void) {
  langListeners.add(cb);
  window.addEventListener("storage", cb);
  return () => {
    langListeners.delete(cb);
    window.removeEventListener("storage", cb);
  };
}

function writeLang(l: Lang) {
  memoryLang = l;
  try {
    localStorage.setItem(LANG_KEY, l);
  } catch {
    /* storage unavailable: memoryLang still applies */
  }
  langListeners.forEach((cb) => cb());
}

export function AppProvider({ children }: { children: React.ReactNode }) {
  const lang = useSyncExternalStore(subscribeLang, readLang, () => "es" as Lang);
  const [source, setSource] = useState<SourceRequest | null>(null);
  const { data: meta } = useApi<Meta>("/api/meta");
  const { data: health, error: apiError } = useApi<Health_>("/api/health");

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  // shareable links: ?lang=en sets the language once, then the toggle takes over
  useEffect(() => {
    const url = new URL(window.location.href);
    const l = url.searchParams.get("lang");
    if (l === "es" || l === "en" || l === "pt") {
      writeLang(l);
      url.searchParams.delete("lang");
      window.history.replaceState(null, "", url.pathname + (url.search || "") + url.hash);
    }
  }, []);

  const setLang = useCallback((l: Lang) => writeLang(l), []);

  const value = useMemo<AppContext>(() => ({
    lang,
    setLang,
    t: (key, vars) => translate(lang, key, vars),
    label: (group, code) => {
      if (!code) return "–";
      const entry = meta?.[group]?.[code] as Record<Lang, string> | undefined;
      return entry?.[lang] ?? code;
    },
    country: (code) => meta?.countries[code]?.names[lang] ?? code,
    meta,
    health,
    apiError,
    source,
    openSource: setSource,
    closeSource: () => setSource(null),
  }), [lang, setLang, meta, health, apiError, source]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp(): AppContext {
  const v = useContext(Ctx);
  if (!v) throw new Error("useApp outside AppProvider");
  return v;
}
