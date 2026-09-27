"use client";

import { Cpu, RotateCcw } from "lucide-react";
import { useEffect, useRef } from "react";
import ChatComposer from "@/components/chat/ChatComposer";
import { useChat } from "@/components/chat/ChatProvider";
import ChatThread from "@/components/chat/ChatThread";
import { useApp } from "@/components/providers";
import { PageHeader } from "@/components/ui";
import { useApi } from "@/lib/useApi";

export default function AskPage() {
  const { t, lang, health } = useApp();
  const { messages, reset, ask } = useChat();
  const { data: sugg } = useApi<{ suggestions: { id: string; text: string }[] }>(`/api/ask/suggestions?lang=${lang}`);
  const autoAsked = useRef(false);

  // deep link: /ask?q=<suggestion id> asks that question right away
  useEffect(() => {
    if (autoAsked.current || !sugg) return;
    const q = new URLSearchParams(window.location.search).get("q");
    const s = sugg.suggestions.find((x) => x.id === q);
    if (s) {
      autoAsked.current = true;
      void ask(s.text);
    }
  }, [sugg, ask]);

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader title={t("ask.title")} subtitle={t("ask.sub")}>
        {messages.length > 0 && (
          <button onClick={reset} className="inline-flex items-center gap-1.5 text-[13px] text-slate-500 hover:text-slate-900">
            <RotateCcw className="h-3.5 w-3.5" /> {t("ask.new")}
          </button>
        )}
      </PageHeader>

      {health && !health.ai_enabled && (
        <div className="mb-4 flex items-start gap-2 rounded-lg bg-emerald-50/70 p-3 text-[13px] text-emerald-900 ring-1 ring-emerald-100">
          <Cpu className="mt-0.5 h-4 w-4 shrink-0" /> {t("ask.local_note")}
        </div>
      )}

      <ChatThread welcome={t("chat.welcome")} starters={(sugg?.suggestions ?? []).map((s) => s.text).concat(t("chat.q.how"), t("chat.q.real"))} />

      <div className="sticky bottom-4 mt-6">
        <ChatComposer autoFocus />
      </div>
    </div>
  );
}
