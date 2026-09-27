"use client";

import clsx from "clsx";
import { BookOpen, Bot, Calculator, ChevronDown, Cpu, Database, Search, Sparkles, Tag } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import Answer from "../Answer";
import { useApp } from "../providers";
import { Badge } from "../ui";
import { type ChatMessage, type TraceStep, useChat } from "./ChatProvider";

function fmt(v: unknown): string {
  if (typeof v === "number") return Number.isInteger(v) ? v.toLocaleString() : v.toLocaleString(undefined, { maximumFractionDigits: 4 });
  return v === null || v === undefined ? "" : String(v);
}

/** Reveals text progressively, never cutting inside a [citation] or leaving bold unclosed. */
function prefersReducedMotion() {
  return typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

function useReveal(text: string, active: boolean, onDone: () => void) {
  const [animate] = useState(() => active && !prefersReducedMotion());
  const [n, setN] = useState(animate ? 0 : text.length);
  const done = useRef(false);
  useEffect(() => {
    if (!animate) return;
    // a timer (not animation frames) keeps revealing even in a background tab
    const frames = Math.min(Math.max(text.length / 9, 28), 95);
    const step = Math.max(2, Math.ceil(text.length / frames));
    let i = 0;
    const timer = setInterval(() => {
      i = Math.min(i + step, text.length);
      setN(i);
      if (i >= text.length) clearInterval(timer);
    }, 16);
    return () => clearInterval(timer);
  }, [text, animate]);
  useEffect(() => {
    if (active && n >= text.length && !done.current) {
      done.current = true;
      onDone();
    }
  }, [n, text.length, active, onDone]);
  let part = text.slice(0, n);
  const open = part.lastIndexOf("[");
  if (open > part.lastIndexOf("]")) part = part.slice(0, open);
  if ((part.match(/\*\*/g) || []).length % 2 === 1) part += "**";
  return { part, finished: n >= text.length };
}

function Trace({ steps }: { steps: TraceStep[] }) {
  const { t, openSource } = useApp();
  const [open, setOpen] = useState(false);
  if (!steps.length) return null;
  return (
    <div className="mt-3 border-t border-slate-100 pt-2">
      <button onClick={() => setOpen((o) => !o)} className="flex items-center gap-1 text-[12px] font-medium text-slate-500 hover:text-slate-800">
        <ChevronDown className={clsx("h-3.5 w-3.5 transition-transform", open && "rotate-180")} />
        {t("ask.trace")} ({steps.length})
      </button>
      {open && (
        <ol className="mt-2 space-y-2">
          {steps.map((s, i) => s.tool === "intent" ? (
            <li key={i} className="rounded-lg bg-blue-50/60 p-2.5 ring-1 ring-blue-100">
              <p className="flex flex-wrap items-center gap-1.5 text-[12px] font-semibold text-slate-700">
                <Tag className="h-3.5 w-3.5" /> {t("ask.intent", { intent: t(`intent.${s.intent}`) })}
                <span className="font-normal text-slate-500">· {Math.round((s.confidence ?? 0) * 100)}%</span>
                {s.low_confidence && <span className="font-normal text-amber-700">· {t("ask.low")}</span>}
              </p>
              {s.entities && Object.keys(s.entities).length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {Object.entries(s.entities).map(([k, v]) => <span key={k} className="rounded bg-white px-1.5 py-0.5 text-[11.5px] text-slate-600 ring-1 ring-slate-200">{k}: {Array.isArray(v) ? v.join(", ") : String(v)}</span>)}
                </div>
              )}
            </li>
          ) : s.tool === "service" || s.tool === "knowledge_base" ? (
            <li key={i} className="flex items-center gap-1.5 rounded-lg bg-slate-50 p-2.5 text-[12px] text-slate-600 ring-1 ring-slate-100">
              {s.tool === "service" ? <Calculator className="h-3.5 w-3.5" /> : <BookOpen className="h-3.5 w-3.5" />}
              <span className="font-semibold text-slate-700">{s.tool === "service" ? t("ask.service") : t("ask.kb")}</span> · <code className="font-mono text-[11.5px]">{s.purpose}</code>
            </li>
          ) : (
            <li key={i} className="rounded-lg bg-slate-50 p-2.5 ring-1 ring-slate-100">
              <p className="flex items-center gap-1.5 text-[12px] font-semibold text-slate-700">
                {s.tool === "run_sql" ? <Database className="h-3.5 w-3.5" /> : <Search className="h-3.5 w-3.5" />}
                {s.tool === "run_sql" ? t("ask.sql") : t("ask.search")}
                {s.purpose && <span className="font-normal text-slate-500">· {s.purpose}</span>}
              </p>
              <pre className="mt-1.5 overflow-x-auto whitespace-pre-wrap rounded bg-slate-900 p-2 font-mono text-[11px] text-emerald-200">{s.query}{s.project_code ? `  [${s.project_code}]` : ""}</pre>
              {s.error && <p className="mt-1 text-[12px] text-red-700">{s.error}</p>}
              {s.columns && s.rows && (
                <div className="mt-2 overflow-x-auto">
                  <table className="text-[11px]">
                    <thead><tr>{s.columns.map((c) => <th key={c} className="border-b border-slate-200 px-2 py-1 text-left font-semibold text-slate-500">{c}</th>)}</tr></thead>
                    <tbody>{s.rows.slice(0, 6).map((r, ri) => <tr key={ri}>{r.map((v, ci) => <td key={ci} className="border-b border-slate-100 px-2 py-1 tabular-nums">{fmt(v)}</td>)}</tr>)}</tbody>
                  </table>
                  <p className="mt-1 text-[11px] text-slate-400">{t("ask.rows", { n: s.row_count ?? s.rows.length })}</p>
                </div>
              )}
              {s.hits && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {s.hits.map((h, hi) => (
                    <button key={hi} onClick={() => openSource({ kind: "source", document_id: h.document_id, locator: `p.${h.page}` })}
                      className="rounded bg-white px-1.5 py-0.5 text-[11px] text-[#1c5cab] ring-1 ring-slate-200 hover:bg-blue-50">
                      {h.project_code} · {h.title} · p.{h.page}
                    </button>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export function BotAvatar({ size = "sm" }: { size?: "sm" | "md" }) {
  return (
    <div className={clsx("flex shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-[#132a45] to-[#2a78d6] text-white shadow-sm",
      size === "sm" ? "h-7 w-7" : "h-9 w-9")}>
      <Bot className={size === "sm" ? "h-4 w-4" : "h-5 w-5"} />
    </div>
  );
}

function AssistantBubble({ m, isLast, compact }: { m: ChatMessage; isLast: boolean; compact: boolean }) {
  const { t } = useApp();
  const { settle, ask, busy } = useChat();
  const { part, finished } = useReveal(m.content, !!m.animate, () => settle(m.id));
  const res = m.res;
  return (
    <div className="flex items-start gap-2">
      <BotAvatar />
      <div className={clsx("min-w-0 flex-1 rounded-2xl rounded-tl-md bg-white ring-1 ring-black/[0.07]", compact ? "px-3.5 py-3" : "p-5")}>
        {!compact && res && (
          <div className="mb-2 flex flex-wrap items-center gap-2">
            {res.engine === "claude" ? <Badge tone="blue"><Sparkles className="h-3 w-3" /> {t("ask.engine.claude")}</Badge>
              : res.engine === "local" ? <Badge tone="green"><Cpu className="h-3 w-3" /> {t("ask.engine.local")}</Badge> : <Badge tone="red">{t("common.error")}</Badge>}
            {res.engine === "local" && res.intent && <Badge>{t(`intent.${res.intent}`)}</Badge>}
          </div>
        )}
        {res?.warning && <p className="mb-2 text-[12px] text-amber-700">{res.warning}</p>}
        <div className={compact ? "text-[13.5px] [&_.prose-answer]:text-[13.5px]" : ""}>
          <Answer text={part} citations={res?.citations ?? []} />
        </div>
        {finished && res?.table && (
          <div className="mt-2 overflow-x-auto">
            <table className="min-w-full text-[12px]">
              <thead><tr>{res.table.columns.map((c) => <th key={c} className="border-b border-slate-200 px-2 py-1.5 text-left font-semibold text-slate-500">{c}</th>)}</tr></thead>
              <tbody>{res.table.rows.map((r, ri) => <tr key={ri}>{r.map((v, ci) => <td key={ci} className="border-b border-slate-100 px-2 py-1.5 tabular-nums">{String(v)}</td>)}</tr>)}</tbody>
            </table>
          </div>
        )}
        {finished && <Trace steps={res?.trace ?? []} />}
        {finished && isLast && (res?.followups?.length || res?.suggestions?.length) ? (
          <div className="mt-3">
            <p className="mb-1.5 text-[11.5px] font-medium text-slate-400">{t("chat.next")}</p>
            <div className="flex flex-wrap gap-1.5">
              {(res?.followups ?? res?.suggestions?.map((s) => s.text) ?? []).slice(0, 3).map((q) => (
                <button key={q} disabled={busy} onClick={() => ask(q)}
                  className="rounded-full bg-blue-50 px-3 py-1 text-left text-[12.5px] text-[#1c5cab] ring-1 ring-blue-100 hover:bg-blue-100 disabled:opacity-50">{q}</button>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function Typing() {
  const { t } = useApp();
  return (
    <div className="flex items-center gap-2" aria-live="polite" aria-label={t("chat.typing")}>
      <BotAvatar />
      <div className="flex items-center gap-1 rounded-2xl rounded-tl-md bg-white px-4 py-3 ring-1 ring-black/[0.07]">
        {[0, 150, 300].map((d) => <span key={d} className="h-2 w-2 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: `${d}ms` }} />)}
      </div>
    </div>
  );
}

export default function ChatThread({ welcome, starters, compact = false }: { welcome: string; starters: string[]; compact?: boolean }) {
  const { messages, busy, ask } = useChat();
  const end = useRef<HTMLDivElement>(null);
  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant")?.id;

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  return (
    <div className="space-y-3">
      <div className="flex items-start gap-2">
        <BotAvatar />
        <div className={clsx("min-w-0 flex-1 rounded-2xl rounded-tl-md bg-white ring-1 ring-black/[0.07]", compact ? "px-3.5 py-3" : "p-5")}>
          <div className={compact ? "text-[13.5px] [&_.prose-answer]:text-[13.5px]" : ""}><Answer text={welcome} citations={[]} /></div>
          {messages.length === 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {starters.map((q) => (
                <button key={q} disabled={busy} onClick={() => ask(q)}
                  className="rounded-full bg-blue-50 px-3 py-1 text-left text-[12.5px] text-[#1c5cab] ring-1 ring-blue-100 hover:bg-blue-100 disabled:opacity-50">{q}</button>
              ))}
            </div>
          )}
        </div>
      </div>
      {messages.map((m) => m.role === "user" ? (
        <div key={m.id} className="flex justify-end">
          <div className={clsx("max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-[#132a45] text-white", compact ? "px-3.5 py-2 text-[13.5px]" : "px-4 py-2.5 text-[14px]")}>{m.content}</div>
        </div>
      ) : (
        <AssistantBubble key={m.id} m={m} isLast={m.id === lastAssistant} compact={compact} />
      ))}
      {busy && <Typing />}
      <div ref={end} />
    </div>
  );
}
