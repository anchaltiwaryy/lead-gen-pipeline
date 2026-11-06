"""Source-specific discovery: turn known job boards + search dorks into leads.

This is the part of implementation_plan.md's "Target Platforms & Discovery
Sources Roadmap" that is execute-safe: instead of only generic DDG queries, we
emit deterministic per-board queries (dorks) that hit, e.g.:

    site:boards.greenhouse.io Developer Advocate
    site:jobs.lever.co DevRel Engineer
    site:jobs.ashbyhq.com GTM
    site:remotive.io "Developer Advocate" remote
    site:tokyodev.com developer Advocate
    site:instahyre.com DevRel

Board URLs embed the company slug (boards.greenhouse.io/<company>/, jobs.lever.co/<company>/),
so we recover a real company name + a concrete jobs URL without extra lookups,
and hand the lead to the detail crawler for domain recovery + posting_text.

Everything here is DETERMINISTIC (no LLM, no paid API) so it can be verified
offline. DDG still does the searching (free).
"""
import re

# host_pattern: (host fragment, company_path_index). All the major boards put
# the company slug FIRST in the path:
#   boards.greenhouse.io/<company>/jobs/<id>
#   jobs.lever.co/<company>/<id>
#   jobs.ashbyhq.com/<company>
#   apply.workable.com/<company>/j/<id>
BOARD_HOSTS = [
    ("boards.greenhouse.io", 0),
    ("jobs.lever.co", 0),
    ("jobs.ashbyhq.com", 0),
    ("apply.workable.com", 0),
    ("jobs.gemini.com", 0),
    ("jobs.comeet.com", 0),
    ("jobs.rippling.com", 0),
    ("workable.com", 0),
]

# Whole-board domains we can site: search to surface their listings.
SITE_DORKS = [
    "site:boards.greenhouse.io",
    "site:jobs.lever.co",
    "site:jobs.ashbyhq.com",
    "site:apply.workable.com",
    "site:remotive.io",
    "site:workatastartup.com",
    "site:welcometothejungle.com",
    "site:instahyre.com",
    "site:cutshort.io",
    "site:tokyodev.com",
    "site:nofluffjobs.com",
    "site:justjoin.it",
    "site:topstartups.io",
    "site:jobs.onday.io",
]

# Curated dorks (from the plan's section 10) for social feeds.
SOCIAL_DORKS = [
    'site:linkedin.com/posts ("hiring" OR "looking for") ("remote" OR "work from home")',
    '("DM open" OR "looking for intern" OR "hiring remote") ("AI" OR "Full Stack" OR "Next.js")',
]


def _slug_from_path(path: str, seg: int) -> str | None:
    parts = [p for p in path.split("/") if p]
    if len(parts) > seg:
        slug = parts[seg]
        slug = re.sub(r"[\-_]+", " ", slug).strip()
        if slug and slug.lower() not in ("jobs", "careers", "boards", "listings", "j", "recruiting"):
            return slug
    return None


def extract_from_board_url(url: str):
    """If `url` is a known board listing, return (company_slug, host_fragment);
    else None."""
    low = url.lower()
    for frag, seg in BOARD_HOSTS:
        if frag in low:
            host = low.split(frag, 1)[1].lstrip("/")
            slug = _slug_from_path(host, seg)
            return (slug, frag)
    return None


def build_source_queries(roles: list[str], regions: list[str], max_per_role: int = 4) -> list[str]:
    """Deterministic dork queries surface job boards per target role (+region)."""
    outs = []
    seen = set()
    for role in roles:
        compact_role = re.sub(r"\s+", " ", role.strip())
        added = 0
        for d in SITE_DORKS:
            q = f'{d} "{compact_role}"'
            if q not in seen:
                seen.add(q)
                outs.append(q)
                added += 1
            if added >= max_per_role:
                break
        if added == 0:
            # if every dork for this role was already used, still guarantee output
            for d in SITE_DORKS[:2]:
                q = f'{d} "{compact_role}"'
                if q not in seen:
                    seen.add(q)
                    outs.append(q)
                    added += 1
    for region in regions:
        q = f'"{roles[0]}" "{region}" remote startup job listing'
        if q not in seen:
            seen.add(q)
            outs.append(q)
    outs.extend(SOCIAL_DORKS)
    return outs[:90]


def _demo_extract() -> None:
    test_urls = [
        "https://boards.greenhouse.io/embark/jobs/124?gh_src=",
        "https://jobs.lever.co/notion-labs/a1b2c3",
        "https://jobs.ashbyhq.com/perplexity-ai",
        "https://apply.workable.com/mercado/j/abc123",
        "https://anyboard.co/jobs",
    ]
    for u in test_urls:
        print(u, "->", extract_from_board_url(u))


if __name__ == "__main__":
    q = build_source_queries(["Developer Advocate", "DevRel Engineer"], ["Europe", "US"])
    print(f"{len(q)} source dorks")
    for s in q[:12]:
        print(" -", s)
    print("--- board URL extraction ---")
    _demo_extract()