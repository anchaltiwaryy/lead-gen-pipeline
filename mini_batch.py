import sys
import os
sys.path.insert(0, ".")

from db import get_conn
from scrape_company_page import scrape_company_detail, update_lead
from qualify import qualify_leads
from enrich_email import enrich_qualified
from draft_email import draft_enriched
from send_gmail import stage_send
from export_results import run_exports

def run_mini_batch():
    conn = get_conn()
    
    # Get a small batch of reachable 'new' leads
    cur = conn.execute("SELECT * FROM leads WHERE status='new' LIMIT 15")
    leads = [dict(r) for r in cur.fetchall()]
    
    scraped_count = 0
    print(f"Scraping up to {len(leads)} leads...")
    
    # Process sequentially to avoid ThreadPoolExecutor hangs
    for lead in leads:
        print(f"  Scraping {lead['company']}...")
        try:
            fields = scrape_company_detail(lead)
            if fields.get("posting_text") or fields.get("role_title") or fields.get("email"):
                update_lead(conn, lead["id"], **fields)
                scraped_count += 1
                print(f"    -> Scraped successfully!")
            else:
                update_lead(conn, lead["id"], status="skipped")
                print(f"    -> No usable page. Marked as skipped.")
        except Exception as e:
            update_lead(conn, lead["id"], status="skipped")
            print(f"    -> Failed: {e}. Marked as skipped.")
            
    print(f"\n[Scrape] {scraped_count} leads successfully scraped with posting_text.")
    if scraped_count == 0:
        print("Nothing to qualify/enrich.")
        return

    qualified = qualify_leads(limit=15)
    print(f"[Qualify] {qualified} leads passed qualification.")
    
    if qualified == 0:
        return
        
    enriched = enrich_qualified(limit=15)
    print(f"[Enrich] {enriched} emails found.")
    
    drafted = draft_enriched(limit=15)
    print(f"[Draft] {drafted} emails drafted.")
    
    stage_send(limit=15)
    print(f"[Gmail] Uploaded drafts to Gmail.")
    
    run_exports()
    print("[Export] CSVs exported.")

if __name__ == "__main__":
    run_mini_batch()
