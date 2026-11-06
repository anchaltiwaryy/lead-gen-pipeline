"""Agent 2 - Web Intelligence Agent.

Deep-crawls target entity domains with Scrapling:
  1. Fast plain-HTTP fetch first.
  2. Falls back to stealth headless Chromium when JS rendering is needed.

All outbound fetches are guarded by the 7-day domain cache (cache.py) so
already-scraped domains never trigger a network round-trip.
"""
from __future__ import annotations

import concurrent.futures as cf
from typing import Optional

import scrape_company_page
from cache import cached_scrape
from config import MAX_ACTIONS_PER_RUN
from db import get_conn, get_leads_by_status, update_lead
from logger import log


class WebIntelAgent:
    """Crawls careers/team/about pages and extracts structured signals."""

    name = "web_intel"

    def __init__(self, limit: int = MAX_ACTIONS_PER_RUN, max_workers: int = 2):
        self.limit = limit
        self.max_workers = max_workers

    @cached_scrape()
    def _cached_fetch(self, url: str) -> str:
        """7-day-cached raw page text for a URL (network shielded by cache)."""
        page = scrape_company_page._fetch(url)
        if page is None:
            return ""
        return scrape_company_page._page_text(page)

    def crawl(self, lead: dict) -> dict:
        """Full detail extraction for one lead (returns update fields dict)."""
        return scrape_company_page.scrape_company_detail(lead)

    def run(self, limit: Optional[int] = None) -> int:
        """Enrich all pending 'new' leads that lack posting_text."""
        conn = get_conn()
        batch = [
            lead for lead in get_leads_by_status(conn, "new", limit=limit or self.limit)
            if not (lead.get("posting_text") or "").strip()
        ]
        conn.close()
        if not batch:
            log.info("[web_intel] no new leads to crawl")
            return 0

        done = 0
        conn = get_conn()
        with cf.ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            futs = {ex.submit(self.crawl, lead): lead for lead in batch}
            for fut in cf.as_completed(futs):
                lead = futs[fut]
                try:
                    fields = fut.result()
                except Exception as e:
                    log.error(f"[web_intel] failed for {lead['company']}: {e}")
                    continue
                if fields.get("posting_text") or fields.get("role_title") or fields.get("email"):
                    update_lead(conn, lead["id"], **fields)
                    done += 1
                else:
                    update_lead(conn, lead["id"], status="skipped")
        conn.close()
        log.info(f"[web_intel] enriched {done}/{len(batch)} leads")
        return done

    def __repr__(self) -> str:
        return f"<WebIntelAgent limit={self.limit}>"