"use client";

import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useApp } from "../providers";
import type { Citation } from "../Answer";

export interface TraceStep {
  tool: "run_sql" | "search_documents" | "intent" | "service" | "knowledge_base";
  intent?: string;
  confidence?: number;
  low_confidence?: boolean;
  followup?: boolean;
  entities?: Record<string, unknown>;
  purpose?: string;
  query: string;
  project_code?: string | null;
  columns?: string[];
  rows?: unknown[][];
  row_count?: number;
  error?: string;
  hits?: { document_id: number; title: string; project_code: string | null; page: number }[];
}

export interface AskResponse {
  answer: string;
  citations: Citation[];
  trace: TraceStep[];
  engine: "claude" | "local" | "error";
  intent?: string;
  confidence?: number;
  table?: { columns: string[]; rows: (string | number)[][] } | null;
  warning?: string;
  suggestions?: { id: string; text: string }[];
  followups?: string[];
  context?: { intent: string; entities: Record<string, unknown> };
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  res?: AskResponse;
  animate?: boolean;
}

interface ChatContext {
  messages: ChatMessage[];
  busy: boolean;
  open: boolean;
  setOpen: (v: boolean) => void;
  ask: (question: string) => Promise<void>;
  openWith: (question: string) => void;
  reset: () => void;
  settle: (id: number) => void;
}

const Ctx = createContext<ChatContext | null>(null);
const MIN_THINKING_MS = 650; // a short pause reads as "thinking" instead of a flash

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const { lang, t } = useApp();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const nextId = useRef(1);
  const busyRef = useRef(false);

  const ask = useCallback(async (question: string) => {
    const q = question.trim();
    if (!q || busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    const context = [...messages].reverse().find((m) => m.role === "assistant" && m.res?.context)?.res?.context ?? null;
    setMessages((m) => [...m, { id: nextId.current++, role: "user", content: q }]);
    const started = Date.now();
    let msg: ChatMessage;
    try {
      const res = await api<AskResponse>("/api/ask", { method: "POST", body: JSON.stringify({ question: q, lang, history, context }) });
      msg = { id: nextId.current++, role: "assistant", content: res.answer, res, animate: true };
    } catch (e) {
      const err = (e as Error).message;
      msg = { id: nextId.current++, role: "assistant", content: err === "network" ? t("shell.api_down") : err,
        res: { answer: "", citations: [], trace: [], engine: "error" } };
    }
    const wait = MIN_THINKING_MS - (Date.now() - started);
    if (wait > 0) await new Promise((r) => setTimeout(r, wait));
    setMessages((m) => [...m, msg]);
    busyRef.current = false;
    setBusy(false);
  }, [messages, lang, t]);

  const value = useMemo<ChatContext>(() => ({
    messages, busy, open, setOpen, ask,
    openWith: (question: string) => { setOpen(true); void ask(question); },
    reset: () => setMessages([]),
    settle: (id: number) => setMessages((m) => m.map((x) => (x.id === id ? { ...x, animate: false } : x))),
  }), [messages, busy, open, ask]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useChat(): ChatContext {
  const v = useContext(Ctx);
  if (!v) throw new Error("useChat outside ChatProvider");
  return v;
}
