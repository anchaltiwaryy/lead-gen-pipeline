"use client";

import { STATUS_FLOW, type LeadFilters, type LeadStatus } from "@/lib/api";
import { Search, SlidersHorizontal } from "lucide-react";

const TABS: { key: LeadStatus | ""; label: string }[] = [
  { key: "", label: "All" },
  ...STATUS_FLOW.map((s) => ({ key: s.key as LeadStatus, label: s.label })),
  { key: "rejected", label: "Rejected" },
];

export default function FilterBar({
  filters,
  onChange,
  sources,
}: {
  filters: LeadFilters;
  onChange: (f: LeadFilters) => void;
  sources: string[];
}) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-surface-600/60 bg-surface-800 p-3">
      <div className="flex flex-wrap items-center gap-2">
        {TABS.map((t) => (
          <button
            key={t.key || "all"}
            onClick={() => onChange({ ...filters, status: t.key })}
            className={`chip transition-colors ${
              filters.status === t.key
                ? "bg-accent text-white"
                : "bg-surface-700 text-slate-400 hover:bg-surface-600"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-[220px] flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            value={filters.search_query || ""}
            onChange={(e) => onChange({ ...filters, search_query: e.target.value })}
            placeholder="Search company, role, domain…"
            className="w-full rounded-lg border border-surface-600 bg-surface-700 py-2 pl-9 pr-3 text-sm outline-none focus:border-accent"
          />
        </div>

        <div className="flex items-center gap-2 text-sm">
          <SlidersHorizontal className="h-4 w-4 text-slate-500" />
          <input
            type="range"
            min={0}
            max={100}
            value={filters.min_score ?? 0}
            onChange={(e) =>
              onChange({ ...filters, min_score: Number(e.target.value) })
            }
            className="accent-indigo-500"
          />
          <span className="w-10 font-mono text-slate-300">
            ≥{filters.min_score ?? 0}
          </span>
        </div>

        <select
          value={filters.source || ""}
          onChange={(e) =>
            onChange({ ...filters, source: e.target.value || undefined })
          }
          className="rounded-lg border border-surface-600 bg-surface-700 px-2 py-2 text-sm outline-none focus:border-accent"
        >
          <option value="">All sources</option>
          {sources.map((s) => (
            <option key={s} value={s}>
              {s.length > 40 ? s.slice(0, 40) + "…" : s}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}