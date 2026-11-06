"""Crawl company pages for all `new` leads (web intelligence stage only)."""
import scrape_company_page as s

n = s.enrich_new_leads(limit=400)
print("DONE crawled:", n, flush=True)
