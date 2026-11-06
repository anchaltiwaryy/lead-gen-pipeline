"""Run scrape -> qualify -> enrich -> draft on a small batch of 25 leads."""
import scrape_company_page
import qualify
import enrich_email
import draft_email

print("Scraping 25 leads...")
scrape_company_page.enrich_new_leads(limit=25)

print("Qualifying up to 25 leads...")
qualify.qualify_leads(limit=25)

print("Enriching up to 25 leads...")
try:
    enrich_email.enrich_qualified(limit=25)
except TypeError:
    enrich_email.enrich_qualified()

print("Drafting up to 25 leads...")
try:
    draft_email.draft_enriched(limit=25)
except TypeError:
    draft_email.draft_enriched()

print("Done processing batch.")
