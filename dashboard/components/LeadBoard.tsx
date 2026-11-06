"use client";

import type { LeadSummary } from "@/lib/api";
import LeadCard from "./LeadCard";
import { Inbox } from "lucide-react";

export default function LeadBoard({
  leads,
  loading,
  onSelect,
}: {
  leads: LeadSummary[];
  loading: boolean;
  onSelect: (lead: LeadSummary) => void;
}) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="card animate-pulse bg-surface-700/50"
            style={{ height: 140 }}
          />
        ))}
      </div>
    );
  }

  if (leads.length === 0) {
    return (
      <div className="card flex flex-col items-center gap-3 py-16 text-slate-500">
        <Inbox className="h-10 w-10" />
        <p className="text-sm">No leads match the current filters.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {leads.map((lead) => (
        <LeadCard key={lead.id} lead={lead} onSelect={onSelect} />
      ))}
    </div>
  );
}