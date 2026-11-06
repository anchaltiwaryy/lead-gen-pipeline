"""Agent 4 - Multi-Tier Contact Enrichment Agent.

Cascading resolution waterfall (see AGENTS.md):
  Tier 0: Free public website emails (email_confidence='public').
  Tier 1a: Apollo.io Web Session API (APOLLO_COOKIE).
  Tier 1b: Apollo.io REST API (APOLLO_API_KEY).
  Tier 2 & 3: Pattern generation + single-session SMTP RCPT-TO verification
              with anti-catchall detection.

SMTP deliverability results are cached 30 days per MX host.
"""
from __future__ import annotations

import random
import time
from typing import Optional

from cache import cached_smtp
from config import GUESSED_EMAILS_TO_DRAFT
from db import get_conn, get_leads_by_status, update_lead
from logger import log
import enrich_email


class EnrichmentAgent:
    """Cascades qualified leads through 4 tiers until a contact email is found."""

    name = "enrichment"

    def __init__(self, guessed_to_draft: bool = GUESSED_EMAILS_TO_DRAFT,
                 limit: int = 25):
        self.guessed_to_draft = guessed_to_draft
        self.limit = limit

    @cached_smtp()
    def _mx_smtp_reachable(self, mx_host: str) -> str:
        """30-day-cached SMTP deliverability probe for an MX host."""
        session = enrich_email._open_mx_session(mx_host)
        if session is None:
            return "unreachable"
        try:
            session.quit()
        except Exception:
            pass
        return "reachable"

    def enrich(self, lead: dict, conn) -> bool:
        """Resolve one lead; returns True if a usable email was stored."""
        name = (lead.get("contact_name") or "").strip()
        domain = (lead.get("company_domain") or "").strip()
        company = lead.get("company") or ""

        # Tier 0: public email already scraped -> accept directly
        if lead.get("email_confidence") == "public" and lead.get("email"):
            update_lead(conn, lead["id"],
                        linkedin_url=enrich_email.build_linkedin_search_url(company, "", ""),
                        status="enriched")
            return True

        if not domain:
            update_lead(conn, lead["id"], status="skipped")
            return False

        apollo_data = None
        if enrich_email.APOLLO_COOKIE:
            apollo_data = enrich_email.apollo_session_lookup(domain, company)
            time.sleep(random.uniform(2.0, 4.0))  # polite throttle
        if not apollo_data and enrich_email.APOLLO_API_KEY:
            apollo_data = enrich_email.apollo_lookup(domain, company)

        if apollo_data and apollo_data.get("email"):
            fields = {"email": apollo_data["email"],
                      "email_confidence": "verified", "status": "enriched"}
            if apollo_data.get("contact_name"):
                fields["contact_name"] = apollo_data["contact_name"]
            if apollo_data.get("contact_title"):
                fields["contact_title"] = apollo_data["contact_title"]
            fields["linkedin_url"] = (apollo_data.get("linkedin_url")
                                      or enrich_email.build_linkedin_search_url(company, "", ""))
            update_lead(conn, lead["id"], **fields)
            return True

        email, conf = None, "none"
        if name:
            first, last = enrich_email.split_name(name)
            email, conf = enrich_email.find_email(first, last, domain)
        if not email:
            email, conf = enrich_email._find_generic_email(domain)

        update_lead(conn, lead["id"],
                    email=email,
                    email_confidence=conf,
                    linkedin_url=enrich_email.build_linkedin_search_url(company, "", ""),
                    status=enrich_email.gate_status(conf, bool(email)))
        return bool(email)

    def run(self, limit: Optional[int] = None) -> int:
        conn = get_conn()
        leads = get_leads_by_status(conn, "qualified", limit=limit or self.limit)
        done = 0
        for lead in leads:
            try:
                if self.enrich(lead, conn):
                    done += 1
            except Exception as e:
                log.error(f"[enrich] failed for {lead['company']}: {e}")
        conn.close()
        log.info(f"[enrich] resolved contacts for {done} leads")
        return done

    def __repr__(self) -> str:
        return f"<EnrichmentAgent limit={self.limit}>"