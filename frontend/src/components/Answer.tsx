"use client";

import { FileSearch } from "lucide-react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useApp } from "./providers";

export interface Citation {
  document_id: number;
  page: number | null;
  locator?: string;
  title: string;
  filename: string;
}

function preprocess(text: string): string {
  return text
    .replace(/\[src:(\d+)\|([^\]]+)\]/g, (_m, id, loc) => ` [§${id}](#loc-${id}-${encodeURIComponent(loc)})`)
    .replace(/\[doc:(\d+)(?:\s*p\.(\d+))?\]/g, (_m, id, pg) => ` [§${id}:${pg || 1}](#src-${id}-${pg || 1})`)
    .replace(/(?<![[\w/-])((?:EC|PE|BR)-\d{4})(?![\w\]])/g, "[$1](/projects/$1)");
}

export default function Answer({ text, citations }: { text: string; citations: Citation[] }) {
  const { openSource } = useApp();
  return (
    <div className="prose-answer text-[14px] text-slate-700">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => {
            if (href?.startsWith("#loc-")) {
              const rest = href.slice(5);
              const id = Number(rest.slice(0, rest.indexOf("-")));
              const loc = decodeURIComponent(rest.slice(rest.indexOf("-") + 1));
              const c = citations.find((x) => x.document_id === id && x.locator === loc) ?? citations.find((x) => x.document_id === id);
              return (
                <button
                  type="button"
                  onClick={() => openSource({ kind: "source", document_id: id, locator: loc })}
                  className="mx-0.5 inline-flex max-w-[280px] items-center gap-1 truncate rounded-md bg-emerald-50 px-1.5 py-0 align-baseline text-[11.5px] font-medium text-emerald-800 ring-1 ring-emerald-200 hover:bg-emerald-100"
                  title={c?.filename}
                >
                  <FileSearch className="h-3 w-3 shrink-0" />
                  <span className="truncate">{loc}</span>
                </button>
              );
            }
            if (href?.startsWith("#src-")) {
              const [, id, pg] = href.split("-");
              const c = citations.find((x) => x.document_id === Number(id) && x.page === Number(pg)) ?? citations.find((x) => x.document_id === Number(id));
              return (
                <button
                  type="button"
                  onClick={() => openSource({ kind: "source", document_id: Number(id), locator: `p.${pg}` })}
                  className="mx-0.5 inline-flex max-w-[260px] items-center gap-1 truncate rounded-md bg-blue-50 px-1.5 py-0 align-baseline text-[11.5px] font-medium text-[#1c5cab] ring-1 ring-blue-200 hover:bg-blue-100"
                  title={c?.filename}
                >
                  <FileSearch className="h-3 w-3 shrink-0" />
                  <span className="truncate">{c ? `${c.title} · p.${pg}` : `doc ${id} · p.${pg}`}</span>
                </button>
              );
            }
            if (href?.startsWith("/projects/")) {
              return <Link href={href} className="font-semibold text-[#2a78d6] hover:underline">{children}</Link>;
            }
            return <a href={href} target="_blank" rel="noreferrer" className="text-[#2a78d6] underline">{children}</a>;
          },
        }}
      >
        {preprocess(text)}
      </ReactMarkdown>
    </div>
  );
}
