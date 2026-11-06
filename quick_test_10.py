"""Quick test run for 10 leads -> exports to a dedicated standalone CSV & Google Sheet."""
import os
import csv
import sys
from db import get_conn, update_lead, count_by_status
from query_gen import generate_queries
from discover_startups import discover_startups
from scrape_company_page import scrape_company_detail
from qualify import qualify_leads, score_lead
from enrich_email import enrich_qualified
from draft_email import draft_enriched
from resume_profile import load_profile
from logger import log

EXPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")
os.makedirs(EXPORTS_DIR, exist_ok=True)
TEST_CSV_PATH = os.path.join(EXPORTS_DIR, "test_run_10_leads.csv")


def run_quick_10_test():
    log.info("=== Starting Quick Test Run (Target: 10 Leads) ===")
    conn = get_conn()
    
    # 1. Discover fresh leads using 2 targeted queries
    log.info("[1/5] Discovering new prospects via search...")
    queries = generate_queries()
    # Filter down to 2 top queries for fast execution
    fast_queries = {
        "funding_queries": (queries.get("funding_queries") or [])[:1],
        "hiring_queries": (queries.get("hiring_queries") or [])[:1],
        "source_queries": (queries.get("source_queries") or [])[:2],
    }
    discover_startups(fast_queries, limit=4)
    
    # 2. Pick up to 10 'new' leads to process
    cur = conn.execute("SELECT * FROM leads WHERE status='new' ORDER BY created_at DESC LIMIT 10")
    new_leads = [dict(r) for r in cur.fetchall()]
    
    if not new_leads:
        # Fallback to any recent leads
        cur = conn.execute("SELECT * FROM leads ORDER BY created_at DESC LIMIT 10")
        new_leads = [dict(r) for r in cur.fetchall()]
        
    log.info(f"[2/5] Crawling web intelligence for {len(new_leads)} prospects...")
    profile = load_profile()
    
    for idx, lead in enumerate(new_leads, 1):
        log.info(f"  ({idx}/{len(new_leads)}) Scraping {lead['company']}...")
        try:
            fields = scrape_company_detail(lead)
            if fields.get("posting_text") or fields.get("role_title") or fields.get("email"):
                update_lead(conn, lead["id"], **fields)
            else:
                update_lead(conn, lead["id"], status="skipped")
        except Exception as e:
            log.warning(f"  Scrape failed for {lead['company']}: {e}")
            update_lead(conn, lead["id"], status="skipped")
            
    # 3. AI Qualify
    log.info("[3/5] Qualifying prospect fit with LLM reasoning...")
    qualify_leads(limit=10)
    
    # 4. Contact Enrichment (Apollo + SMTP)
    log.info("[4/5] Resolving and verifying decision-maker contacts...")
    enrich_qualified(limit=10)
    
    # 5. Personalized Outreach Drafting
    log.info("[5/5] Synthesizing context and drafting personalized outreach...")
    draft_enriched(limit=10)
    
    # 6. Export 10 processed leads to dedicated CSV
    cur = conn.execute("SELECT * FROM leads ORDER BY created_at DESC LIMIT 10")
    processed_10 = [dict(r) for r in cur.fetchall()]
    
    if processed_10:
        fieldnames = list(processed_10[0].keys())
        with open(TEST_CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(processed_10)
        log.info(f"Saved dedicated test results to: {TEST_CSV_PATH}")
        
    # 7. Push to Google Sheets (if token present)
    sheet_url = None
    try:
        from sheets_push import get_service, push
        # Push to dedicated test spreadsheet
        service = get_service()
        info = service.spreadsheets().create(
            body={"properties": {"title": "Lead Intelligence Engine - Test Run (10 Leads)"}}
        ).execute()
        sid = info["spreadsheetId"]
        
        # Prepare values for Sheet
        values = [list(processed_10[0].keys())] + [[str(v or "") for v in row.values()] for row in processed_10]
        service.spreadsheets().values().update(
            spreadsheetId=sid,
            range="Sheet1!A1",
            valueInputOption="RAW",
            body={"values": values},
        ).execute()
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sid}"
        log.info(f"Google Sheet created: {sheet_url}")
    except Exception as e:
        log.warning(f"Google Sheets sync note: {e}")
        
    print("\n" + "="*60)
    print("✅ QUICK TEST RUN COMPLETED (10 LEADS)")
    print(f"📁 Local CSV Export: {TEST_CSV_PATH}")
    if sheet_url:
        print(f"📊 Google Spreadsheet: {sheet_url}")
    print("="*60)
    print(f"\nFinal DB Status Summary: {count_by_status(conn)}")


if __name__ == "__main__":
    run_quick_10_test()
