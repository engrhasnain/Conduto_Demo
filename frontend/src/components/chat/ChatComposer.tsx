"use client";

import clsx from "clsx";
import { SendHorizontal } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useApp } from "../providers";
import { useChat } from "./ChatProvider";

/** Message box: Enter sends, Shift+Enter adds a line, grows with the text. */
export default function ChatComposer({ autoFocus = false, compact = false }: { autoFocus?: boolean; compact?: boolean }) {
  const { t } = useApp();
  const { ask, busy } = useChat();
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (autoFocus) ref.current?.focus();
  }, [autoFocus]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }, [text]);

  function send() {
    if (!text.trim() || busy) return;
    void ask(text);
    setText("");
  }

  return (
    <form onSubmit={(e) => { e.preventDefault(); send(); }}
      className={clsx("flex items-end gap-2 bg-white ring-1 ring-black/[0.08]", compact ? "rounded-xl p-1.5" : "rounded-2xl p-2 shadow-lg")}>
      <textarea
        ref={ref}
        rows={1}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
        placeholder={t("chat.placeholder")}
        aria-label={t("chat.placeholder")}
        className="max-h-[120px] min-h-[36px] flex-1 resize-none bg-transparent px-2.5 py-2 text-[14px] leading-snug outline-none"
      />
      <button type="submit" disabled={busy || !text.trim()} aria-label={t("ask.send")}
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#132a45] text-white transition-opacity disabled:opacity-30">
        <SendHorizontal className="h-4 w-4" />
      </button>
    </form>
  );
}
