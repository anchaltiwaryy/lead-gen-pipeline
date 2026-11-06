# Replace YC Scraper → Global Startup Discovery Engine — DONE

> Status: fully implemented and verified. All items below are complete.

The old pipeline scraped YC's directory (Airbnb, Coinbase, DoorDash — the
opposite of what's wanted). Replaced with a DuckDuckGo-driven global startup
discovery engine targeting recently funded (seed/A/B), small-to-mid-sized
startups across many regions.

## Final Architecture

```
AI generates ~40 search queries per region/sector/role combo (query_gen.py, Groq)
    ↓
DuckDuckGo News & Web Search (FREE) — retries with backoff (DDG intermittently throttles)
    ↓
AI (Groq) extracts structured data: company, domain, funding, stage, region, founder
    ↓
domain-recovery fallback if Groq missed the domain concept
    ↓
careers crawler (scrape_company_page.py): /careers /jobs /about -> posting_text
    ↓
Rest of pipeline unchanged (qualify → enrich → draft → send)
```

## Status of each proposed change

| Change | Status | Notes |
|---|---|---|
| [NEW] `discover_startups.py` | ✅ Done | DDG news/web + Groq extraction + dedup + `source='web_search'` |
| [MOD] `query_gen.py` | ✅ Done | outputs `funding_queries` + `hiring_queries` (not `yc_tags`) |
| [MOD] `scrape_company_page.py` | ✅ Done | rewrote for real company career/team pages; removed YC selectors |
| [MOD] `config.py` | ✅ Done | TARGET_REGIONS, STARTUP_STAGES, MAX_EMPLOYEES, FUNDING_RECENCY |
| [MOD] `main.py` | ✅ Done | `stage_scrape` → `discover_startups`; YC import removed |
| [DELETE] `scrape_yc.py` | ✅ Done | removed |
| [MOD] `db.py` | ✅ Done | columns: `region`, `funding_stage`, `employee_count`, `news_url` |
| [NEW] `discovery_sources.py` | ✅ Done | executes the **Target Platforms & Discovery Sources Roadmap** (below): deterministic per-board dorks (`site:` queries for Greenhouse/Lever/Ashby/Workable + Wellfound/Otta/TokyoDev/Instahyre/Cutshort + LinkedIn/X dorks) with `extract_from_board_url` -> company slug + real job URL, no LLM, no paid API |
| [MOD] `query_gen.py` | ✅ Done | `generate_queries()` now also returns `source_queries` (deterministic dorks appended to the LLM output) |
| [MOD] `discover_startups.py` | ✅ Done | consumes `source_queries`; board-listing results become leads directly via `_board_leads_from_results` (bypasses the LLM extraction for them) |

---

## Target Platforms & Discovery Sources Roadmap — EXECUTED in `discovery_sources.py`

> Status: implemented as the deterministic source-dork layer. The platforms below
> are reached via `site:` search dorks (free, no API keys); when a result's URL
> is a company careers board (Greenhouse/Lever/Ashby/Workable/etc.) the company
> slug + job listing URL are extracted directly. Social-feed dorks (LinkedIn/X)
> are included verbatim from section 10.

The discovery engine queries and scrapes across the following target sources, ecosystem directories, VC portfolio boards, and search dorks:

### 1. Startup Funding & Venture Tracking
- **Crunchbase**: Comprehensive database of global startups, funding rounds (Seed, Series A/B), and VC investments.
- **PitchBook**: Institutional-grade tracking for recently funded ventures, private equity, and emerging startups.
- **Y Combinator (Work at a Startup)**: Direct portal for YC-backed companies hiring globally for full-time and intern roles.
- **Topstartups.io**: Filters fast-growing startups backed by top VCs (Sequoia, a16z, YC) by remote status and funding stage.
- **Startups.gallery**: Curated directory tracking high-growth, venture-backed remote startups.

### 2. Global Remote-First Platforms
- **Wellfound (formerly AngelList)**: Primary board for early-to-growth stage startups with global remote and internship filters.
- **Himalayas.app**: Clean remote board with exact timezone and geographical restrictions (e.g., "Everywhere in the World").
- **We Work Remotely (WWR)**: One of the largest global remote boards with dedicated full-time and internship/junior listings.
- **Remotive**: Filters remote tech listings specifically by region and "Worldwide" eligibility.
- **Arc.dev**: Vetted remote platform matching international developers and interns with global startups.
- **RealWorkFromAnywhere**: Dedicated explicitly to roles that do not require regional tax residency or specific country borders.

### 3. Europe & UK Startup Boards
- **Otta (Welcome to the Jungle)**: Tech and startup platform focused on curated European and UK roles.
- **EU-Startups Job Board**: European startup news outlet with an integrated job board for remote roles.
- **The Hub**: Nordic and broader European startup portal specifically featuring paid startup internships and early-stage roles.
- **WorkInStartups**: UK-based board focused on London and UK remote startup hiring.
- **NoFluffJobs**: European board featuring transparent salary ranges and remote options across the EU.
- **JustJoin.it**: High-volume tech job board for European software, data, and AI startups with remote filters.

### 4. Japan Tech Platforms
- **TokyoDev**: Specialized platform for English-speaking tech talent looking for remote or relocation-friendly roles in Japan.
- **Japan Dev**: Vetted Japanese tech companies and fast-growing startups featuring "Global Remote" filters.

### 5. Dubai & Middle East (MENA) Platforms
- **Magnitt**: Tracks venture investments, startup funding, and tech ecosystems across Dubai, Saudi Arabia, and the MENA region.
- **eFinancialCareers**: Widely used in Dubai/UAE for fintech, quantitative engineering, and tech startup roles.
- **GrabJobs UAE**: Regional job aggregator with filters for remote tech setups based out of Dubai and Abu Dhabi.
- **Bayt**: Regional Middle Eastern portal with dedicated remote and startup search parameters.

### 6. Open-Source & Alternative Sources
- **GitHub (awesome-remote-job Repositories)**: Community-maintained markdown lists of 100% remote-first engineering and product companies.
- **Nitter**: Lightweight, privacy-focused frontends used to scrape X (Twitter) for funding announcements and founder hiring posts without authentication walls.

### 7. Indian Startup Funding & Deal Trackers
- **Inc42 DataLabs**: The primary source for tracking Indian tech startup funding rounds (Seed through Series C+), weekly deal roundups, and startup launches.
- **Entrackr / YourStory**: Real-time reporting on early-stage Indian fundraising, stealth-mode startups, financial teardowns, and VC investments.
- **Tracxn**: Comprehensive database for Indian startups, tracking recent funding, investor portfolios, and emerging tech sectors.
- **Startup India Portal**: Official government-backed platform tracking registered Indian startups, incubator cohorts, and non-dilutive government grants.

### 8. Niche Indian Tech & Startup Job Boards
- **Cutshort.io**: AI-driven hiring platform engineered specifically for Indian tech and product startups, allowing candidates to bypass recruiters and connect directly with founders or tech leads.
- **Instahyre**: Matches developers and product talent directly with venture-backed Indian startups. Known for unlisted roles that aren't posted on generic boards.
- **Cuvette**: A specialized platform focusing on tech internships and entry-level developer roles at vetted Indian startups, featuring mandatory stipend and salary transparency.
- **Wellfound (India Region)**: Filter explicitly for India-based Seed and Series A startups offering fully remote software, AI, or growth roles.
- **Unstop (formerly Dare2Compete)**: The dominant platform for Indian tech college students and recent grads for hackathons, hiring challenges, and remote startup internships.

### 9. VC Portfolio Career Networks (India & Global)
- **Peak XV Partners (formerly Sequoia India)**: Dedicated talent network listing software, AI, and design roles across Peak XV portfolio startups.
- **Blume Ventures Portfolio Jobs**: High-growth Indian early-stage startups hiring across engineering, AI, and operations.
- **Elevation Capital & Accel India Career Boards**: Direct listings for early-stage companies backed by major tier-1 VCs operating in India.
- **Antler India**: Focuses on pre-seed and seed-stage startups, frequently looking for founding engineers, interns, and early tech team members.

### 10. Reverse-Engineering Hiring on Social Feeds (X & LinkedIn)
- **LinkedIn Boolean Search**:
  `site:linkedin.com/posts ("hiring" OR "looking for") ("remote" OR "work from home") ("intern" OR "founding engineer") ("Bangalore" OR "Gurgaon" OR "India" OR "US" OR "EU")`
- **X (Twitter) Dorking**:
  `("DM open" OR "looking for intern" OR "hiring remote") ("AI" OR "Full Stack" OR "Next.js" OR "DevRel") ("India" OR "Europe" OR "US")`

---

## Open questions — resolved

- **Wipe `leads.db`?** ✅ Yes — reset to start with real early-stage startups.
- **Serper.dev backup?** ✅ No — stayed free-only. DDG throttling handled inside
  `discover_startups` with retry + backoff; no paid fallback needed.

## Key decisions confirmed during implementation

1. **`_search_ddg` retries (3) with backoff** — DDG reliably returns empty on
   transient throttling; isolated tests showed 0 → 12 results on retry.
2. **Keep `hiring_queries` key** (renamed from `careers`): code + plan aligned.
3. **`scrape_company_page` must NOT skip leads just because `company_domain` is
   set** — discovery always sets it, so the old skip dead-ended all web leads.
4. **Domain recovery**: when Groq can't confirm a domain, `discover_startups`
   does a quick DDG lookup for `"{company} official website domain"`.

## Verification (passed)

```powershell
python query_gen.py                    # 38 queries, correct roles/regions ✓
python discover_startups.py            # inserts real startups into leads.db ✓
python view_leads.py                   # inspect rows ✓
python main.py --scrape-only           # orchestration ✓
python discovery_sources.py            # dorks + board-URL extraction ✓
python -c "from discover_startups import _board_leads_from_results"  # board leads ✓
```

## Resolved notes

- Secret keys live in a git-ignored `.env` (moved `GROQ_API_KEY` and friends out
  of `config.py`). `config.py` is now untracked + git-ignored. If the old value
  was pushed, rotate it.
- `scrape_yc.py` is deleted; nothing references its `yc_tags` API anymore.