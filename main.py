"""Orchestrator - runs the full AI-directed lead intelligence engine with logging & alerts.

Stages:
0  resume_profile   -> build candidate profile (or reuse cached resume_profile.json)
0.5 query_gen       -> targeted, source-specific search queries from profile
1  discover         -> DuckDuckGo search -> AI extract entities -> status='new'
1b detail           -> per-company web intelligence: posting_text, domain, contact
2  qualify (AI)     -> gate: only fit >= threshold move to 'qualified'
3  enrich           -> multi-tier contact resolution (Apollo session/API, SMTP)
4  draft  (AI)      -> personalized outreach on 'enriched' only
5  send             -> Gmail draft (default) or send

Run with:  python main.py [--scrape-only] [--qualify-only] [--enrich-only]
            [--draft-only] [--send-only]
"""
import sys
from db import get_conn, count_by_status
from logger import log
from notify import send_alert

import resume_profile
import query_gen
import discover_startups
import scrape_company_page
import qualify
import enrich_email
import draft_email
import send_gmail


def stage_profile() -> None:
    log.info("=== STAGE 0: Profile Analysis ===")
    try:
        resume_profile.load_profile()
        log.info("[profile] using cached resume_profile.json")
    except FileNotFoundError:
        log.info("[profile] building profile from resume.pdf...")
        resume_profile.build_resume_profile()


def stage_scrape() -> None:
    log.info("=== STAGE 0.5 & 1: Search Intelligence & Discovery ===")
    queries = query_gen.generate_queries()
    total_q = sum(len(v) for v in queries.values() if isinstance(v, list))
    log.info(f"[scrape] generated {total_q} discovery queries")
    discover_startups.discover_startups(queries)
    scrape_company_page.enrich_new_leads()


def stage_qualify() -> None:
    log.info("=== STAGE 2: AI Qualification Gate ===")
    qualify.qualify_leads()


def stage_enrich() -> None:
    log.info("=== STAGE 3: Multi-Tier Contact Enrichment ===")
    enrich_email.enrich_qualified()


def stage_draft() -> None:
    log.info("=== STAGE 4: Personalized Outreach Generation ===")
    draft_email.draft_enriched()


def stage_send() -> None:
    log.info("=== STAGE 5: Gmail Delivery Engine ===")
    send_gmail.stage_send()


def summary() -> dict:
    conn = get_conn()
    counts = count_by_status(conn)
    log.info("--- Pipeline Lead Status Summary ---")
    log.info(str(counts))
    conn.close()
    return counts


STAGES = {
    "scrape": stage_scrape,
    "qualify": stage_qualify,
    "enrich": stage_enrich,
    "draft": stage_draft,
    "send": stage_send,
}


def main() -> None:
    only = None
    for arg in sys.argv[1:]:
        if arg.startswith("--") and arg.endswith("-only"):
            only = arg[2:-5]
            break

    try:
        stage_profile()
        if only:
            if only not in STAGES:
                log.error(f"Unknown stage '{only}'. Options: {list(STAGES)}")
                return
            STAGES[only]()
        else:
            for fn in STAGES.values():
                fn()
        counts = summary()
        send_alert("Pipeline Execution Complete", "Autonomous lead intelligence run completed successfully.", counts)
    except Exception as e:
        log.error(f"Pipeline crashed with error: {e}", exc_info=True)
        send_alert("Pipeline Execution Error", str(e), is_error=True)
        raise e


if __name__ == "__main__":
    main()