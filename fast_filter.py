import sys
sys.path.insert(0, ".")
from db import get_conn
import concurrent.futures as cf
from scrape_company_page import _crawl_pages, scrape_company_detail, update_lead
from qualify import qualify_leads
from enrich_email import enrich_qualified
from draft_email import draft_enriched
from send_gmail import stage_send
from export_results import run_exports

conn = get_conn()
cur = conn.execute("SELECT * FROM leads WHERE status='new' ORDER BY created_at")
leads = [dict(r) for r in cur.fetchall()]

def check_lead(lead):
    domain = lead.get('company_domain')
    if not domain:
        return lead, False
    try:
        pages = _crawl_pages(domain)
        if pages and pages[0][1] is not None:
            return lead, True
    except:
        pass
    return lead, False

good_leads = []
bad_leads = []

print(f"Filtering {len(leads)} leads...")
for lead in leads:
    _, is_good = check_lead(lead)
    if is_good:
        good_leads.append(lead)
        if len(good_leads) >= 5:
            break
    else:
        bad_leads.append(lead)

print(f"Found {len(good_leads)} good leads.")

print("Running pipeline on guaranteed good leads...")
scraped_count = 0
for lead in good_leads:
    try:
        fields = scrape_company_detail(lead)
        if fields.get("posting_text") or fields.get("role_title") or fields.get("email"):
            update_lead(conn, lead["id"], **fields)
            scraped_count += 1
            print(f"  -> Scraped: {lead['company']}")
        else:
            update_lead(conn, lead["id"], status="skipped")
            print(f"  -> Skipped (AI found no matches): {lead['company']}")
    except Exception as e:
        update_lead(conn, lead["id"], status="skipped")
        print(f"  -> Failed: {lead['company']}")

print(f"Scraped count: {scraped_count}")
if scraped_count > 0:
    q = qualify_leads(limit=5)
    print(f"Qualified count: {q}")
    if q > 0:
        e = enrich_qualified(limit=5)
        print(f"Enriched count: {e}")
        d = draft_enriched(limit=5)
        print(f"Drafted count: {d}")
        stage_send(limit=5)
        print("Gmail upload done.")
        
run_exports()
print("Exports done.")
