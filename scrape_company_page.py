"""Stage 1b - per-company detail enrichment (AI-parsed careers crawler).

Discovery lands 'new' leads with company/domain/funding but no posting_text.
This stage crawls the company's careers/team pages in parallel, then uses Groq
to extract:
  - the job posting(s) that genuinely match TARGET_ROLES
  - a posting_text / role_title for the best match
  - a contact name (founder/CEO/HR) from the team section
  - any *public* email addresses listed on the page (free, reliable contact)

Public emails found on the corporate page are stored with
email_confidence='public' so the enrich stage SKIPS SMTP for them — that is the
fast+free path. Everything else leaves the email to SMTP verification.

Fast, not fragile:
  - plain-HTTP Fetcher first; headless browser only as fallback
  - candidate career paths fetched in PARALLEL with a short per-page timeout
  - batches across leads are also run concurrently
  - domains that don't resolve are skipped in seconds
"""
import re
import json
import socket
import concurrent.futures as cf

from tld import get_fld
from scrapling.fetchers import StealthyFetcher, Fetcher
from db import get_conn, get_leads_by_status, update_lead
from config import (
    MAX_ACTIONS_PER_RUN, GROQ_API_KEY, GROQ_MODEL, GROQ_CRAWL_MODEL,
    GEMINI_API_KEY, TARGET_ROLES,
)

EXCLUDED_DOMAINS = {
    "ycombinator.com", "startupschool.org", "linkedin.com", "twitter.com",
    "facebook.com", "crunchbase.com", "instagram.com", "youtube.com",
    "fortune.com", "reuters.com", "techcrunch.com", "axios.com", "thehustle.co",
}

# Candidate paths, ordered by likely value. Fetched in parallel; the richest
# page wins.
CAREER_PATHS = ["/careers", "/jobs", "/about", "/team"]

_PARSE_PROMPT = """Extract the most relevant software/GTM/DevRel job postings for a candidate
whose target roles are: {roles}

Below is the raw text of a startup's careers/team/about pages.

Return ONLY valid JSON:
{{
  "matches": [
    {{
      "title": "job title from the page",
      "posting_text": "2-5 sentence description of THIS role as written on the page (requirements + responsibilities). Only use text that actually appears on the page; never invent.",
      "fit_score_hint": 0-100
    }}
  ],
  "contact": {{
    "name": "founder/CEO/CTO/HR contact person full name if visible on the pages, else null",
    "title": "their title, else null"
  }},
  "public_emails": ["any hello@/info@/team@/founders@/hr@ addresses visibly listed on these pages, else []"] 
}}

RULES:
- Include ONLY roles whose title OR description genuinely matches: {target}
- If no real match exists, matches: []
- Never fabricate posting_text content.
Page text:
{page_text}
"""


def _fetch(url: str, timeout: int = 5):
    """Fast HTTP first; headless browser only when plain fetch returns empty."""
    try:
        page = Fetcher.get(url, timeout=timeout)
        content = _page_text(page)
        if page and page.status == 200 and len(content) > 120:
            return page
    except Exception:
        pass
    try:
        return StealthyFetcher.fetch(url, headless=True, timeout=5000, retries=1)
    except Exception:
        return None


def _page_text(page) -> str:
    try:
        if hasattr(page, "get_all_text"):
            txt = page.get_all_text()
        elif hasattr(page, "text"):
            txt = page.text
        else:
            txt = ""
        if isinstance(txt, bytes):
            txt = txt.decode("utf-8", errors="replace")
        return re.sub(r"\n{2,}", "\n", str(txt)).strip()
    except Exception:
        return ""


def _crawl_pages(domain: str) -> list[tuple[str, object]]:
    """Walk candidate paths in order and stop at the first usable page."""
    hit = None
    empty = 0
    for path in CAREER_PATHS:
        url = f"https://{domain}{path}"
        page = _fetch(url)
        if page is None:
            empty += 1
            if empty >= 2:
                break
            continue
        txt = _page_text(page)
        if len(txt) >= 300:
            hit = (url, page)
            break
        empty += 1
        if empty >= 2:
            break
    return [hit] if hit else []


def _best_page_text(pages: list[tuple[str, object]]) -> str:
    """Text of the single best page crawled"""
    if not pages:
        return ""
    # pages is already short-circuited to the first good hit by _crawl_pages
    return _page_text(pages[0][1])[:6000]


def _parse_with_ai(page_text: str) -> dict:
    if not page_text:
        return {"matches": [], "contact": None, "public_emails": None}
    prompt = _PARSE_PROMPT.format(
        target=", ".join(TARGET_ROLES),
        roles=", ".join(TARGET_ROLES),
        page_text=page_text[:5000],
    )
    parsed = None
    if GEMINI_API_KEY:
        try:
            from google import genai
            from config import GEMINI_MODEL
            client = genai.Client(api_key=GEMINI_API_KEY)
            raw = client.models.generate_content(model=GEMINI_MODEL, contents=prompt).text
            text = raw.strip().strip("```json").strip("```").strip()
            parsed = json.loads(text)
        except Exception:
            parsed = None

    if not parsed and GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            completion = client.chat.completions.create(
                model=GROQ_CRAWL_MODEL,
                messages=[
                    {"role": "system", "content": "You extract structured job data from web page text. Output valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            parsed = json.loads(completion.choices[0].message.content)
        except Exception:
            parsed = None

    if not parsed:
        return {"matches": [], "contact": None, "public_emails": None}
    if isinstance(parsed, dict):
        return parsed
    return {"matches": [], "contact": None, "public_emails": None}


def _board_emails(page_text: str, domain: str) -> list[str]:
    """Any user@domain emails actually printed on the page -> free public address."""
    out = []
    for m in re.finditer(r"[\w.+-]+@([\w-]+\.)+[\w-]+", page_text):
        addr = m.group(0).strip(".,;")
        try:
            fld = get_fld(addr.split("@")[1], fix_protocol=True)
        except Exception:
            continue
        if fld == domain and addr not in out:
            out.append(addr)
    return out


def _social_urls(pages: list[tuple[str, object]]) -> dict:
    """Scan crawled page HTML for LinkedIn company/profile + X/Twitter links.

    Returns {"linkedin_company_url", "linkedin_contact_url", "x_url"} (best
    guesses, often empty). Companies list their own profiles on their sites, so
    this is a free + reliable signal that complements email enrichment.
    """
    html = " ".join(
        (p.html_content or "") if hasattr(p, "html_content") else _page_text(p)
        for _, p in pages
        if hasattr(p, "html_content")
    )
    hrefs = re.findall(r'href="(https?://(?:[^"]*linkedin\.com|www\.linkedin\.com)[^"]*)"', html)
    hrefs += re.findall(r'href="(https?://(?:www\.|x\.com|twitter\.com)[^"]*)"', html)
    hrefs = list(dict.fromkeys(hrefs))

    linkedin_company = None
    linkedin_contact = None
    x_url = None
    for h in hrefs:
        low = h.lower()
        if "linkedin.com/company" in low and not linkedin_company:
            linkedin_company = h
        elif ("linkedin.com/in/" in low or "linkedin.com/in " in low or "linkedin.com/in" in low) and not linkedin_contact:
            linkedin_contact = h
        elif "linkedin.com" in low:
            # any other linkedin link (people, company mgmt) -> contact if none yet
            linkedin_contact = linkedin_contact or h
        elif ("x.com/" in low or "twitter.com/" in low) and not x_url:
            x_url = h
    return {
        "linkedin_company_url": linkedin_company,
        "linkedin_contact_url": linkedin_contact,
        "x_url": x_url,
    }


def scrape_company_detail(lead: dict) -> dict:
    company = lead.get("company") or ""
    domain = (lead.get("company_domain") or "").strip()
    if not domain:
        domain = _extract_domain(lead.get("job_url") or "") or ""
    if not domain:
        from discover_startups import _resolve_domain
        for cand in _resolve_domain(company):
            if cand:
                domain = cand
                break
    if not domain:
        return {"company_domain": None, "role_title": None, "posting_text": None}

    # Fail fast: DNS
    try:
        socket.gethostbyname(domain)
    except socket.gaierror:
        return {"company_domain": None, "role_title": None, "posting_text": None}

    pages = _crawl_pages(domain)
    page_text = _best_page_text(pages)
    data = _parse_with_ai(page_text)
    matches = data.get("matches") or []
    contact = data.get("contact") or {}
    emails = data.get("public_emails") or []
    if not emails:
        emails = _board_emails(page_text, domain)

    role_title = None
    posting = None
    if matches:
        def _score(m):
            return int(m.get("fit_score_hint") or 0)
        m = max(matches, key=_score)
        role_title = m.get("title", "").strip()
        posting = (m.get("posting_text") or "").strip()

    fields = {
        "company_domain": domain,
        "role_title": role_title or None,
        "posting_text": posting or (page_text or ""),
        "contact_name": (contact.get("name") or lead.get("contact_name") or None),
        "contact_title": (contact.get("title") or lead.get("contact_title") or None),
    }
    fields.update(_social_urls(pages))
    # Public email: mark direct so enrich skips SMTP for it.
    candidates = [e for e in emails if e and e.lower().endswith(domain.lower())]
    if candidates:
        fields["email"] = candidates[0]
        fields["email_confidence"] = "public"
    return fields


def enrich_new_leads(limit: int = MAX_ACTIONS_PER_RUN) -> int:
    conn = get_conn()
    leads = [
        lead for lead in get_leads_by_status(conn, "new", limit=limit)
        if not (lead.get("posting_text") or "").strip()
    ]
    if not leads:
        print("[detail] no new leads to enrich.")
        return 0

    done = 0
    # max_workers=2: keeps concurrency low to avoid hammering Groq rate limits
    # and prevents the executor from getting stuck behind multiple dead sites.
    with cf.ThreadPoolExecutor(max_workers=2) as ex:
        futs = {ex.submit(scrape_company_detail, lead): lead for lead in leads}
        for fut in cf.as_completed(futs):
            lead = futs[fut]
            try:
                fields = fut.result()
            except Exception as e:
                print(f"[detail] failed for {lead['company']}: {e}")
                continue
            if fields.get("posting_text") or fields.get("role_title") or fields.get("email"):
                update_lead(conn, lead["id"], **fields)
                done += 1
            else:
                update_lead(conn, lead["id"], status="skipped")
                print(f"[detail] no usable page for {lead['company']} (skipped)")
    print(f"[detail] enriched {done}/{len(leads)} leads.")
    return done


def _extract_domain(url: str) -> str | None:
    if not url:
        return None
    try:
        fld = get_fld(url.strip(), fix_protocol=True)
        if fld and fld.lower() not in EXCLUDED_DOMAINS:
            return fld
    except Exception:
        pass
    return None


if __name__ == "__main__":
    enrich_new_leads(limit=MAX_ACTIONS_PER_RUN)