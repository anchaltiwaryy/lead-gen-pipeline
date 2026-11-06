"""
Batch 20 — End-to-end pipeline run for 20 leads.

Stages:
  1. Scrape  - enrich up to 20 'new' leads with posting_text via detail crawler
  2. Qualify - AI-score scraped leads against resume profile (threshold=50)
  3. Enrich  - multi-tier email enrichment (Apollo session -> REST -> SMTP)
  4. Draft   - AI-write personalized outreach emails
  5. Gmail   - upload drafts to Gmail Drafts folder
  6. Export  - write CSVs and push to a NEW separate Google Sheet

Run: python batch_20.py
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BATCH_SIZE = 20

from db import get_conn, count_by_status, get_leads_by_status, update_lead

def separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ── Stage 1: Detail Scraper ──────────────────────────────────────────────────
separator("STAGE 1 — Detail Scraper (filling posting_text)")
from scrape_company_page import enrich_new_leads
scraped = enrich_new_leads(limit=BATCH_SIZE)
print(f"[batch] scraped {scraped} leads.")
time.sleep(2)

# ── Stage 2: Qualify ──────────────────────────────────────────────────────────
separator("STAGE 2 — AI Qualification (threshold=50)")
from qualify import qualify_leads
qualified = qualify_leads(limit=BATCH_SIZE)
print(f"[batch] qualified stage processed {qualified} leads.")
time.sleep(2)

# ── Stage 3: Enrich ───────────────────────────────────────────────────────────
separator("STAGE 3 — Multi-Tier Email Enrichment")
from enrich_email import enrich_qualified
enriched = enrich_qualified(limit=BATCH_SIZE)
print(f"[batch] enriched {enriched} leads.")
time.sleep(2)

# ── Stage 4: Draft ────────────────────────────────────────────────────────────
separator("STAGE 4 — AI Email Drafting")
from draft_email import draft_enriched
drafted = draft_enriched(limit=BATCH_SIZE)
print(f"[batch] drafted {drafted} emails.")
time.sleep(1)

# ── Stage 5: Gmail Upload ─────────────────────────────────────────────────────
separator("STAGE 5 — Gmail Draft Upload")
try:
    from send_gmail import stage_send
    sent = stage_send(limit=BATCH_SIZE)
    print(f"[batch] uploaded {sent} drafts to Gmail.")
except Exception as e:
    print(f"[batch][gmail] WARN: {e}")
    print("[batch][gmail] Skipping Gmail upload — check credentials.json / token.json.")
time.sleep(1)

# ── Stage 6: Export + New Google Sheet ────────────────────────────────────────
separator("STAGE 6 — Export CSVs + Push to New Google Sheet")
try:
    from export_results import run_exports
    run_exports()
    print("[batch] CSVs written to exports/")

    from sheets_push import get_service, push
    svc = get_service()
    # Force a brand-new sheet by passing spreadsheet_id=None and overriding the title
    import sheets_push
    original_title = sheets_push.SPREADSHEET_TITLE
    sheets_push.SPREADSHEET_TITLE = "Startup Pipeline — Batch 20 (Aug 2026)"
    sid = push(svc, spreadsheet_id=None)   # None = always create new sheet
    sheets_push.SPREADSHEET_TITLE = original_title
    print(f"\n[batch] ✅ Google Sheet created!")
    print(f"[batch] Open: https://docs.google.com/spreadsheets/d/{sid}")
except Exception as e:
    print(f"[batch][sheets] WARN: {e}")
    print("[batch][sheets] Check sheets_token.json / credentials.json.")

# ── Final Summary ─────────────────────────────────────────────────────────────
separator("FINAL SUMMARY")
conn = get_conn()
status_counts = count_by_status(conn)
conn.close()
print("DB status counts:", status_counts)
print(f"""
  Scraped      : {scraped}
  Qualified    : {qualified}
  Enriched     : {enriched}
  Drafted      : {drafted}
""")
