import os
import csv
from db import get_conn, count_by_status
from qualify import qualify_leads
from enrich_email import enrich_qualified
from draft_email import draft_enriched
from logger import log

EXPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")
os.makedirs(EXPORTS_DIR, exist_ok=True)
TEST_CSV_PATH = os.path.join(EXPORTS_DIR, "test_run_10_leads.csv")

def finish_test():
    log.info("--- Qualifying, Enriching & Drafting Test Leads ---")
    qualify_leads(limit=10)
    enrich_qualified(limit=10)
    draft_enriched(limit=10)
    
    conn = get_conn()
    cur = conn.execute("SELECT * FROM leads ORDER BY created_at DESC LIMIT 10")
    rows = [dict(r) for r in cur.fetchall()]
    
    if rows:
        fieldnames = list(rows[0].keys())
        with open(TEST_CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
            
    print("\n" + "="*60)
    print("✅ TEST RUN 100% COMPLETE & SAVED TO STANDALONE SHEET")
    print(f"📁 Local CSV Export: {TEST_CSV_PATH}")
    print("="*60)
    print(f"Status Summary: {count_by_status(conn)}")

if __name__ == "__main__":
    finish_test()
