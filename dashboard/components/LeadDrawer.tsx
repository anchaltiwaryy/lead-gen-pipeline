"use client";

import { useCallback, useEffect, useState } from "react";
import {
  api,
  type LeadDetail,
  type LeadStatus,
} from "@/lib/api";
import { scoreColor } from "./LeadCard";
import {
  X,
  Mail,
  Copy,
  ExternalLink,
  MessageSquare,
  Briefcase,
  Send,
  Save,
  Sparkles,
  FileText,
  Brain,
} from "lucide-react";

const STATUS_OPTIONS: LeadStatus[] = [
  "new",
  "qualified",
  "enriched",
  "drafted",
  "draft_created",
  "sent",
  "applied",
  "replied",
  "rejected",
];

function gmailComposeUrl(lead: LeadDetail): string {
  const params = new URLSearchParams({
    view: "cm",
    fs: "1",
    to: lead.email || "",
    su: `Re: ${lead.role_title || "Engineering"} role at ${lead.company}`,
    body: lead.draft_email_body || "",
  });
  return `https://mail.google.com/mail/?${params.toString()}`;
}

function xDmUrl(lead: LeadDetail): string {
  return lead.x_url
    ? lead.x_url.replace("twitter.com", "x.com")
    : "https://x.com/messages";
}

export default function LeadDrawer({
  leadId,
  onClose,
  onChanged,
}: {
  leadId: number | null;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [lead, setLead] = useState<LeadDetail | null>(null);
  const [emailBody, setEmailBody] = useState("");
  const [linkedinNote, setLinkedinNote] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState("");

  const load = useCallback(async () => {
    if (leadId === null) return;
    const d = await api.lead(leadId);
    setLead(d);
    setEmailBody(d.draft_email_body || "");
    setLinkedinNote(d.linkedin_note || "");
    setNotes(d.custom_notes || "");
  }, [leadId]);

  useEffect(() => {
    if (leadId !== null) load();
  }, [leadId, load]);

  if (leadId === null) return null;

  const flash = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(""), 2500);
  };

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text || "");
      flash("Copied to clipboard");
    } catch {
      flash("Clipboard unavailable");
    }
  };

  const open = (url: string | undefined) => {
    if (url) window.open(url, "_blank", "noopener,noreferrer");
  };

  const save = async () => {
    if (!lead) return;
    setSaving(true);
    try {
      await api.editLead(lead.id, {
        draft_email_body: emailBody,
        linkedin_note: linkedinNote,
        custom_notes: notes,
      });
      flash("Saved");
      onChanged();
    } catch (e) {
      flash((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const setStatus = async (status: LeadStatus) => {
    if (!lead) return;
    try {
      await api.updateStatus(lead.id, status);
      setLead({ ...lead, status });
      flash(`Status → ${status}`);
      onChanged();
    } catch (e) {
      flash((e as Error).message);
    }
  };

  const createGmailDraft = async () => {
    if (!lead) return;
    try {
      const res = await api.gmailDraft(lead.id);
      setLead({ ...lead, gmail_draft_id: res.gmail_draft_id, status: "draft_created" });
      flash("Gmail draft created");
      onChanged();
    } catch (e) {
      flash((e as Error).message);
    }
  };

  const wordCount = emailBody.trim() ? emailBody.trim().split(/\s+/).length : 0;

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/50 backdrop-blur-sm">
      <aside className="flex h-full w-full max-w-2xl flex-col overflow-hidden border-l border-surface-600/60 bg-surface-900 shadow-2xl">
        <header className="flex items-start justify-between gap-3 border-b border-surface-600/60 p-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-white">
                {lead?.company || "Loading…"}
              </h2>
              <span className={`chip ${scoreColor(lead?.fit_score ?? null)}`}>
                {lead?.fit_score ?? "—"}
              </span>
            </div>
            <p className="text-sm text-slate-400">
              {lead?.role_title || "No role title"} · {lead?.region || "Unknown region"}
            </p>
            {lead?.company_domain && (
              <p className="mt-0.5 font-mono text-xs text-slate-500">
                {lead.company_domain}
              </p>
            )}
          </div>
          <button onClick={onClose} className="btn-ghost">
            <X className="h-4 w-4" />
          </button>
        </header>

        {toast && (
          <div className="mx-4 mt-3 rounded-lg bg-accent/20 px-3 py-2 text-sm text-accent-hover">
            {toast}
          </div>
        )}

        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {/* Status */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Status
            </span>
            {STATUS_OPTIONS.map((s) => (
              <button
                key={s}
                onClick={() => setStatus(s)}
                className={`chip transition-colors ${
                  lead?.status === s
                    ? "bg-accent text-white"
                    : "bg-surface-700 text-slate-400 hover:bg-surface-600"
                }`}
              >
                {s}
              </button>
            ))}
          </div>

          {/* Copilot buttons */}
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => open(gmailComposeUrl(lead!))}
              disabled={!lead?.email}
              className="btn-primary"
              title={lead?.email || "No contact email"}
            >
              <Mail className="h-4 w-4" /> Gmail Compose
            </button>
            <button onClick={createGmailDraft} disabled={!lead?.email} className="btn-primary">
              <FileText className="h-4 w-4" /> Create Gmail Draft
            </button>
            <button
              onClick={() => {
                copy(lead?.linkedin_note || "");
                open(lead?.linkedin_contact_url || lead?.linkedin_url || undefined);
              }}
              disabled={!lead?.linkedin_note}
              className="btn-ghost"
            >
              <Copy className="h-4 w-4" /> LinkedIn Note + Profile
            </button>
            <button
              onClick={() => {
                copy(lead?.x_dm || "");
                open(xDmUrl(lead!));
              }}
              className="btn-ghost"
            >
              <MessageSquare className="h-4 w-4" /> Open X Direct DM
            </button>
            <button
              onClick={() => open(lead?.job_url || undefined)}
              disabled={!lead?.job_url}
              className="btn-ghost col-span-2"
            >
              <Briefcase className="h-4 w-4" /> Trigger Wellfound Apply
            </button>
          </div>

          {/* Contact */}
          <section className="card">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Contact
            </h3>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="block text-slate-500">Name</span>
                <span className="text-slate-200">
                  {lead?.contact_name || "—"}
                  {lead?.contact_title ? ` · ${lead.contact_title}` : ""}
                </span>
              </div>
              <div>
                <span className="block text-slate-500">Email</span>
                <span className="font-mono text-emerald-400">
                  {lead?.email || "—"}
                </span>
              </div>
              <div>
                <span className="block text-slate-500">Confidence</span>
                <span className="chip bg-surface-700 text-slate-300">
                  {lead?.email_confidence || "none"}
                </span>
              </div>
              <div>
                <span className="block text-slate-500">Funding</span>
                <span className="text-slate-200">
                  {lead?.funding_stage || "—"} {lead?.funding_info || ""}
                </span>
              </div>
            </div>
          </section>

          {/* AI reasoning */}
          <section className="card">
            <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Brain className="h-3.5 w-3.5" /> AI Fit Reasoning
            </h3>
            <p className="text-sm text-slate-300">{lead?.fit_reason || "No reasoning yet."}</p>
            {lead?.company_context && (
              <p className="mt-2 border-t border-surface-600/60 pt-2 text-sm text-slate-400">
                {lead.company_context}
              </p>
            )}
          </section>

          {/* Career posting */}
          <section className="card">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Scraped Careers Text
            </h3>
            <pre className="max-h-48 overflow-y-auto whitespace-pre-wrap font-sans text-sm text-slate-400">
              {lead?.posting_text || "No posting text scraped."}
            </pre>
            {lead?.news_url && (
              <button
                onClick={() => open(lead.news_url!)}
                className="mt-2 inline-flex items-center gap-1 text-xs text-accent-hover hover:underline"
              >
                <ExternalLink className="h-3 w-3" /> Source article
              </button>
            )}
          </section>

          {/* Editable drafts */}
          <section className="card">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <Sparkles className="h-3.5 w-3.5" /> Outreach Draft
              </h3>
              <span
                className={`chip ${
                  wordCount <= 120 ? "bg-emerald-500/15 text-emerald-400" : "bg-rose-500/20 text-rose-300"
                }`}
              >
                {wordCount}/120 words
              </span>
            </div>
            <textarea
              value={emailBody}
              onChange={(e) => setEmailBody(e.target.value)}
              rows={8}
              className="w-full rounded-lg border border-surface-600 bg-surface-700 p-3 text-sm outline-none focus:border-accent"
              placeholder="Email body (< 120 words)…"
            />
          </section>

          <section className="card">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                LinkedIn Note
              </h3>
              <span
                className={`chip ${
                  linkedinNote.length <= 300 ? "bg-emerald-500/15 text-emerald-400" : "bg-rose-500/20 text-rose-300"
                }`}
              >
                {linkedinNote.length}/300 chars
              </span>
            </div>
            <textarea
              value={linkedinNote}
              onChange={(e) => setLinkedinNote(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-surface-600 bg-surface-700 p-3 text-sm outline-none focus:border-accent"
              placeholder="Connection note (< 300 chars)…"
            />
          </section>

          <section className="card">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Custom Notes
            </h3>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="w-full rounded-lg border border-surface-600 bg-surface-700 p-3 text-sm outline-none focus:border-accent"
              placeholder="Internal notes…"
            />
          </section>
        </div>

        <footer className="flex items-center justify-between gap-3 border-t border-surface-600/60 p-4">
          {lead?.gmail_draft_id && (
            <span className="truncate font-mono text-xs text-slate-500">
              Draft ID: {lead.gmail_draft_id}
            </span>
          )}
          <button onClick={save} disabled={saving} className="btn-primary ml-auto">
            <Save className="h-4 w-4" /> {saving ? "Saving…" : "Save Edits"}
          </button>
        </footer>
      </aside>
    </div>
  );
}