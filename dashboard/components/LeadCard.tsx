"use client";

import type { LeadSummary, LeadStatus } from "@/lib/api";
import {
  Building2,
  MapPin,
  Target,
  Mail,
  MessageSquare,
  Globe,
} from "lucide-react";

const STATUS_STYLES: Record<string, string> = {
  new: "bg-slate-600 text-slate-200",
  qualified: "bg-emerald-500/15 text-emerald-400",
  enriched: "bg-sky-500/15 text-sky-400",
  drafted: "bg-violet-500/15 text-violet-400",
  draft_created: "bg-violet-500/15 text-violet-300",
  sent: "bg-amber-500/15 text-amber-400",
  applied: "bg-amber-500/15 text-amber-400",
  replied: "bg-emerald-500/15 text-emerald-300",
  rejected: "bg-rose-500/15 text-rose-400",
  skipped: "bg-surface-600 text-slate-500",
  needs_review: "bg-orange-500/15 text-orange-400",
};

export function scoreColor(score: number | null): string {
  if (score === null) return "bg-surface-600 text-slate-400";
  if (score >= 85) return "bg-emerald-500/20 text-emerald-300";
  if (score >= 70) return "bg-lime-500/20 text-lime-300";
  if (score >= 50) return "bg-amber-500/20 text-amber-300";
  return "bg-rose-500/20 text-rose-300";
}

export default function LeadCard({
  lead,
  onSelect,
}: {
  lead: LeadSummary;
  onSelect: (lead: LeadSummary) => void;
}) {
  return (
    <button
      onClick={() => onSelect(lead)}
      className="card group text-left transition-colors hover:border-accent/60 hover:bg-surface-700/60"
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <Building2 className="h-4 w-4 shrink-0 text-slate-500" />
          <h3 className="truncate font-semibold text-white">{lead.company}</h3>
        </div>
        <span className={`chip shrink-0 ${scoreColor(lead.fit_score)}`}>
          {lead.fit_score ?? "—"}
        </span>
      </div>

      <p className="mb-3 truncate text-sm text-slate-400">
        {lead.role_title || "No role title"}
      </p>

      <div className="mb-3 flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
        <span className={`chip ${STATUS_STYLES[lead.status] || STATUS_STYLES.new}`}>
          {lead.status}
        </span>
        {lead.region && (
          <span className="inline-flex items-center gap-1">
            <MapPin className="h-3 w-3" />
            {lead.region}
          </span>
        )}
        {lead.funding_stage && <span>{lead.funding_stage}</span>}
      </div>

      <div className="flex items-center gap-3 text-slate-400">
        {lead.email && (
          <span title={lead.email} className="inline-flex items-center gap-1">
            <Mail className="h-3.5 w-3.5 text-emerald-400" />
          </span>
        )}
        {lead.linkedin_url && (
          <span title="LinkedIn">
            <Globe className="h-3.5 w-3.5" />
          </span>
        )}
        {lead.x_url && (
          <span title="X">
            <MessageSquare className="h-3.5 w-3.5" />
          </span>
        )}
        <span className="ml-auto inline-flex items-center gap-1">
          <Target className="h-3 w-3" />
          {lead.source ? (
            <span className="max-w-[140px] truncate">{lead.source}</span>
          ) : (
            "—"
          )}
        </span>
      </div>
    </button>
  );
}