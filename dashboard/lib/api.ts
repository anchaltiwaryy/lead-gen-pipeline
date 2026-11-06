export type LeadStatus =
  | "new"
  | "qualified"
  | "enriched"
  | "drafted"
  | "draft_created"
  | "sent"
  | "applied"
  | "replied"
  | "rejected"
  | "skipped"
  | "needs_review";

export const STATUS_FLOW: { key: LeadStatus; label: string }[] = [
  { key: "new", label: "Discovered" },
  { key: "qualified", label: "Qualified" },
  { key: "enriched", label: "Enriched" },
  { key: "drafted", label: "Drafted" },
  { key: "sent", label: "Sent/Applied" },
  { key: "replied", label: "Replied" },
];

export interface LeadSummary {
  id: number;
  company: string;
  company_domain: string | null;
  role_title: string | null;
  job_url: string | null;
  funding_info: string | null;
  funding_stage: string | null;
  region: string | null;
  employee_count: string | null;
  source: string | null;
  fit_score: number | null;
  fit_reason: string | null;
  contact_name: string | null;
  contact_title: string | null;
  email: string | null;
  email_confidence: string | null;
  linkedin_url: string | null;
  x_url: string | null;
  status: LeadStatus;
  created_at: string;
}

export interface LeadDetail extends LeadSummary {
  posting_text: string | null;
  company_context: string | null;
  news_url: string | null;
  gmail_draft_id: string | null;
  linkedin_company_url: string | null;
  linkedin_contact_url: string | null;
  draft_email_body: string | null;
  linkedin_note: string | null;
  x_dm: string | null;
  custom_notes: string | null;
}

export interface Stats {
  total: number;
  by_status: Record<string, number>;
  score_distribution: Record<string, number>;
  by_source: Record<string, number>;
}

export interface LogLine {
  ts: string;
  level: string;
  message: string;
}

export interface LeadFilters {
  status?: LeadStatus | "";
  min_score?: number;
  source?: string;
  search_query?: string;
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export function leadsUrl(filters: LeadFilters, limit = 50, offset = 0): string {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.min_score !== undefined && filters.min_score > 0)
    params.set("min_score", String(filters.min_score));
  if (filters.source) params.set("source", filters.source);
  if (filters.search_query) params.set("search_query", filters.search_query);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  return `${API_BASE}/api/leads?${params.toString()}`;
}

export const api = {
  listLeads: (filters: LeadFilters, limit = 50) =>
    json<{ total: number; items: LeadSummary[] }>(leadsUrl(filters, limit)),

  lead: (id: number) => json<LeadDetail>(`${API_BASE}/api/leads/${id}`),

  updateStatus: (id: number, status: LeadStatus) =>
    json<{ id: number; status: LeadStatus }>(`${API_BASE}/api/leads/${id}/status`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),

  editLead: (id: number, fields: Partial<Pick<LeadDetail, "draft_email_body" | "linkedin_note" | "x_dm" | "custom_notes">>) =>
    json<{ id: number; updated: string[] }>(`${API_BASE}/api/leads/${id}/edit`, {
      method: "POST",
      body: JSON.stringify(fields),
    }),

  gmailDraft: (id: number) =>
    json<{ id: number; gmail_draft_id: string; status: string }>(
      `${API_BASE}/api/leads/${id}/gmail-draft`,
      { method: "POST", body: JSON.stringify({}) }
    ),

  stats: () => json<Stats>(`${API_BASE}/api/stats`),

  pipelineRun: (stage: string, limit?: number) =>
    json<{ started: boolean; stage: string }>(`${API_BASE}/api/pipeline/run`, {
      method: "POST",
      body: JSON.stringify({ stage, limit: limit ?? null }),
    }),

  logStreamUrl: () => `${API_BASE}/api/pipeline/logs/stream`,
};