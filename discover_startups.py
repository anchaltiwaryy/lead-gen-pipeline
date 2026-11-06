"""Stage 1a - discover recently funded early-stage startups via web search.

Replaces the old YC scraper. Uses DuckDuckGo news + web search (free, no API
key) to find startups that recently raised funding, then uses Groq to parse
the unstructured search results into structured leads.

Flow:
  1. AI generates ~40 targeted search queries (query_gen.py)
  2. DuckDuckGo news search runs each query
  3. Groq parses each batch of search results into structured company data
  4. Deduplicates against existing DB entries
  5. Inserts with source='web_search', status='new'
"""
import json
import time
import random
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None
from config import (
    GROQ_API_KEY, GROQ_MODEL, GEMINI_API_KEY,
    DISCOVERY_QUERIES_PER_RUN, MAX_EMPLOYEES, STARTUP_STAGES,
)
from db import get_conn, insert_lead, count_by_status, already_contacted

EXTRACT_PROMPT = """Extract startup companies from these search results. Look for
recently funded early-stage startups (Seed / Series A / Series B, under {max_emp} employees).

IGNORE:
- Big established companies (1000+ employees, public companies, FAANG, etc.)
- Investor/VC firms themselves
- News outlets, accelerators, or platforms
- Companies where the funding info is unclear or very old

Return ONLY a valid JSON array. Each element:
{{
  "company": "Startup Name",
  "domain": "example.com",
  "funding_stage": "Seed" or "Series A" or "Series B",
  "funding_amount": "$X.XM" or null,
  "region": "Country or region",
  "description": "One line about what they do",
  "news_url": "URL of the funding article",
  "founder_name": "Founder Name" or null
}}

If no valid startups are found, return an empty array: []

Search results:
{results}
"""


def _search_ddg(query: str, max_results: int = 12, retries: int = 3) -> list[dict]:
    """Run a DuckDuckGo web/news search, retrying on DDG's intermittent
    empty/throttled responses with a short backoff."""
    for attempt in range(1, retries + 1):
        try:
            with DDGS() as ddgs:
                try:
                    results = list(ddgs.news(query, max_results=max_results))
                except Exception:
                    results = []
                if not results:
                    # Fallback to web search
                    try:
                        results = list(ddgs.text(query, max_results=max_results))
                    except Exception:
                        results = []
                if results:
                    return results
        except Exception as e:
            print(f"[discover] search attempt {attempt} failed for '{query[:50]}...': {e}")
        # Transient empty/throttle — wait a bit and retry (skip on last attempt)
        if attempt < retries:
            time.sleep(random.uniform(2.0, 4.0))
    return []


def _parse_results_with_ai(results: list[dict]) -> list[dict]:
    """Use Groq to extract structured startup data from raw search results."""
    if not results:
        return []

    # Format results for the LLM
    formatted = []
    for r in results:
        entry = {
            "title": r.get("title", ""),
            "body": r.get("body", r.get("snippet", "")),
            "url": r.get("url", r.get("href", "")),
            "date": r.get("date", r.get("published", "")),
        }
        formatted.append(entry)

    prompt = EXTRACT_PROMPT.format(
        max_emp=MAX_EMPLOYEES,
        results=json.dumps(formatted, indent=1),
    )

    if GEMINI_API_KEY:
        try:
            from google import genai
            from config import GEMINI_MODEL
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            text = response.text.strip().strip("```json").strip("```").strip()
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                for key in ("startups", "companies", "results", "data"):
                    if key in parsed and isinstance(parsed[key], list):
                        return parsed[key]
                return []
            return parsed if isinstance(parsed, list) else []
        except Exception:
            pass

    if GROQ_API_KEY:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You extract structured startup data from search results. Output valid JSON only - a JSON array of objects."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        raw = completion.choices[0].message.content
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            for key in ("startups", "companies", "results", "data"):
                if key in parsed and isinstance(parsed[key], list):
                    return parsed[key]
            return []
        return parsed if isinstance(parsed, list) else []
    raise ValueError("No AI API key configured")


def _resolve_domain(company: str) -> list:
    """Best-effort domain recovery: search '<company> website' and pick a plausible
    registrable domain from the hrefs (or cheerfully the snippet). Returns a list
    of candidate domains (may be empty)."""
    from tld import get_fld
    query = f"{company} official website domain"
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
    except Exception:
        return []

    candidates = []
    for r in results:
        href = (r.get("href") or r.get("url") or "").strip()
        for token in href.replace("http://", " ").replace("https://", " ").split():
            token = token.rstrip(".,;)")
            try:
                fld = get_fld(token, fix_protocol=True)
            except Exception:
                continue
            if fld and fld.lower() not in (
                "google.com", "crunchbase.com", "linkedin.com", "twitter.com",
                "facebook.com", "instagram.com", "youtube.com",
            ) and len(fld) > 3:
                candidates.append(fld)
    # de-dupe, most common first
    from collections import Counter
    return [d for d, _ in Counter(candidates).most_common()] or candidates


def _board_leads_from_results(results: list[dict]) -> list[dict]:
    """Turn results whose URL is a known job-board listing into structured leads.

    Company name comes straight from the board URL slug (no LLM needed), and the
    board listing URL becomes the lead's job_url. Region/role are best-effort
    from the result title+snippet.
    """
    from discovery_sources import extract_from_board_url

    out = []
    seen = set()
    for r in results:
        url = (r.get("url") or r.get("href") or "").strip()
        hit = extract_from_board_url(url)
        if not hit:
            continue
        company, host = hit
        if not company:
            continue
        key = company.lower()
        if key in seen:
            continue
        seen.add(key)
        title = (r.get("title") or "").strip()
        role_title = None
        # strip trailing "- Company  |  company.co" pattern from the title
        import re
        parts = re.split(r"\s*[-|]\s*", title)
        if parts:
            candidate = parts[0].strip()
            if 2 <= len(candidate) <= 60:
                role_title = candidate
        out.append({
            "company": company,
            "url": url,
            "role_title": role_title,
            "region": None,
        })
    return out


def discover_startups(queries: dict, limit: int = DISCOVERY_QUERIES_PER_RUN) -> int:
    """Run search queries and insert discovered startups into the DB."""
    conn = get_conn()
    all_queries = []
    for key in ("funding_queries", "hiring_queries", "source_queries"):
        if key in queries and isinstance(queries[key], list):
            all_queries.extend(queries[key])

    if not all_queries:
        print("[discover] no queries to run!")
        return 0

    # Shuffle to mix regions and query types
    random.shuffle(all_queries)
    all_queries = all_queries[:limit]

    total_inserted = 0
    total_searched = 0
    seen_companies = set()

    # Load existing company names to avoid duplicates
    existing = {
        row["company"].lower()
        for row in conn.execute("SELECT company FROM leads").fetchall()
    }

    for i, query in enumerate(all_queries):
        print(f"[discover] ({i+1}/{len(all_queries)}) searching: {query[:60]}...")
        results = _search_ddg(query)
        total_searched += 1

        if not results:
            continue

        # Source-query path: board listing URLs already encode the company, so
        # take them straight without spending an LLM call on them.
        board_leads = _board_leads_from_results(results)
        for bl in board_leads:
            name = bl["company"]
            name_lower = name.lower()
            if name_lower in seen_companies or name_lower in existing:
                continue
            domain = bl.get("domain") or ""
            if not domain:
                for cand in _resolve_domain(name):
                    if cand:
                        domain = cand
                        break
            if domain:
                import socket
                try:
                    socket.gethostbyname(domain)
                except socket.gaierror:
                    continue
            seen_companies.add(name_lower)
            existing.add(name_lower)
            insert_lead(
                conn,
                company=name,
                job_url=bl["url"],
                role_title=bl.get("role_title"),
                source=query,
                company_domain=domain or None,
                region=bl.get("region"),
                news_url=bl["url"],
                status="new",
            )
            total_inserted += 1
            print(f"[discover][board] {name} ({domain})")

        # Parse with AI for the rest
        startups = _parse_results_with_ai(results)

        for startup in startups:
            name = (startup.get("company") or "").strip()
            if not name:
                continue
            name_lower = name.lower()
            if name_lower in seen_companies or name_lower in existing:
                continue
            seen_companies.add(name_lower)

            domain = (startup.get("domain") or "").strip()
            news_url = (startup.get("news_url") or "").strip()

            # Recover a missing domain so the detail crawler can find career pages.
            if not domain:
                for cand in _resolve_domain(name):
                    if cand:
                        domain = cand
                        break

            # Only keep leads whose domain actually resolves - a bad domain is a
            # dead end for the detail crawler and would sit in 'new' forever.
            if domain:
                import socket
                try:
                    socket.gethostbyname(domain)
                except socket.gaierror:
                    print(f"[discover] skipping {name}: domain {domain} does not resolve")
                    continue

            insert_lead(
                conn,
                company=name,
                job_url=news_url or f"https://{domain}" if domain else "",
                source=query,
                company_domain=domain or None,
                funding_info=startup.get("funding_amount"),
                funding_stage=startup.get("funding_stage"),
                region=startup.get("region"),
                news_url=news_url or None,
                contact_name=startup.get("founder_name"),
                company_context=startup.get("description"),
                status="new",
            )
            total_inserted += 1
            existing.add(name_lower)

        # Polite delay between searches to avoid rate limiting
        if i < len(all_queries) - 1:
            delay = random.uniform(1.5, 3.5)
            time.sleep(delay)

    print(f"\n[discover] searched {total_searched} queries, inserted {total_inserted} new startups.")
    print(f"[discover] DB status: {count_by_status(conn)}")
    return total_inserted


if __name__ == "__main__":
    from query_gen import generate_queries

    print("[discover] generating AI search queries...")
    queries = generate_queries()
    total_q = sum(len(v) for v in queries.values() if isinstance(v, list))
    print(f"[discover] generated {total_q} queries")
    print(json.dumps(queries, indent=2))
    print("\n[discover] starting search...")
    discover_startups(queries)
