import { STATUS_FLOW, type Stats } from "@/lib/api";
import { ArrowDown } from "lucide-react";

function countFor(stats: Stats | null, key: string): number {
  if (!stats) return 0;
  if (key === "sent") {
    return (stats.by_status["sent"] || 0) + (stats.by_status["applied"] || 0);
  }
  return stats.by_status[key] || 0;
}

export default function FunnelBar({ stats }: { stats: Stats | null }) {
  const items = STATUS_FLOW;
  return (
    <div className="flex flex-col items-stretch gap-1 rounded-xl border border-surface-600/60 bg-surface-800 p-3 sm:flex-row sm:items-center sm:gap-0">
      {items.map((s, i) => (
        <div key={s.key} className="flex flex-1 items-center gap-1">
          <div className="flex flex-1 flex-col items-center rounded-lg bg-surface-700/60 px-2 py-2 text-center">
            <span className="text-xl font-bold text-white">
              {countFor(stats, s.key)}
            </span>
            <span className="text-[11px] uppercase tracking-wide text-slate-400">
              {s.label}
            </span>
          </div>
          {i < items.length - 1 && (
            <ArrowDown className="mx-1 hidden h-4 w-4 shrink-0 text-slate-500 sm:block sm:rotate-[-90deg]" />
          )}
        </div>
      ))}
    </div>
  );
}