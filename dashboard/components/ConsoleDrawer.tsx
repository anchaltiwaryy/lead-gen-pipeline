"use client";

import { useEffect, useRef, useState } from "react";
import { api, type LogLine } from "@/lib/api";
import { X, Terminal, Play, Trash2 } from "lucide-react";

const STAGES = [
  { key: "scrape", label: "Scrape" },
  { key: "qualify", label: "Qualify" },
  { key: "enrich", label: "Enrich" },
  { key: "draft", label: "Draft" },
  { key: "send", label: "Send" },
  { key: "all", label: "Full Run" },
];

const LEVEL_COLORS: Record<string, string> = {
  INFO: "text-slate-400",
  SUCCESS: "text-emerald-400",
  ERROR: "text-rose-400",
  WARNING: "text-amber-400",
};

export default function ConsoleDrawer({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [lines, setLines] = useState<LogLine[]>([]);
  const [running, setRunning] = useState<string | null>(null);
  const bodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const es = new EventSource(api.logStreamUrl());
    es.onmessage = (ev) => {
      try {
        const line = JSON.parse(ev.data) as LogLine;
        setLines((prev) => [...prev.slice(-399), line]);
      } catch {
        /* ignore non-JSON frames */
      }
    };
    es.onerror = () => {
      /* EventSource auto-reconnects */
    };
    return () => es.close();
  }, [open]);

  useEffect(() => {
    if (bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }
  }, [lines]);

  if (!open) return null;

  const runStage = async (stage: string) => {
    setRunning(stage);
    try {
      await api.pipelineRun(stage);
    } catch (e) {
      setLines((prev) => [
        ...prev,
        { ts: new Date().toISOString(), level: "ERROR", message: (e as Error).message },
      ]);
    } finally {
      setTimeout(() => setRunning(null), 4000);
    }
  };

  return (
    <div className="fixed inset-0 z-40 flex justify-start bg-black/50 backdrop-blur-sm">
      <aside className="flex h-full w-full max-w-xl flex-col border-r border-surface-600/60 bg-surface-900 shadow-2xl">
        <header className="flex items-center justify-between border-b border-surface-600/60 p-4">
          <div className="flex items-center gap-2">
            <Terminal className="h-5 w-5 text-accent-hover" />
            <h2 className="font-bold text-white">Live Pipeline Console</h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setLines([])}
              className="btn-ghost"
              title="Clear console"
            >
              <Trash2 className="h-4 w-4" />
            </button>
            <button onClick={onClose} className="btn-ghost">
              <X className="h-4 w-4" />
            </button>
          </div>
        </header>

        <div className="flex flex-wrap gap-2 border-b border-surface-600/60 p-3">
          {STAGES.map((s) => (
            <button
              key={s.key}
              onClick={() => runStage(s.key)}
              disabled={running !== null}
              className={`btn text-xs ${
                running === s.key ? "btn-primary" : "btn-ghost"
              }`}
            >
              <Play className="h-3.5 w-3.5" /> {s.label}
            </button>
          ))}
        </div>

        <div ref={bodyRef} className="flex-1 space-y-1 overflow-y-auto bg-black/40 p-3 font-mono text-xs">
          {lines.length === 0 && (
            <p className="text-slate-600">Waiting for pipeline output…</p>
          )}
          {lines.map((l, i) => (
            <div key={i} className="flex gap-2">
              <span className="shrink-0 text-slate-600">
                {l.ts.slice(11, 19)}
              </span>
              <span className={`shrink-0 w-14 ${LEVEL_COLORS[l.level] || "text-slate-400"}`}>
                {l.level}
              </span>
              <span className="break-words text-slate-300">{l.message}</span>
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}