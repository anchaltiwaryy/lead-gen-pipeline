# 🤖 Autonomous AI-Powered Lead Intelligence Engine

> **“I built an AI-powered lead intelligence engine for organizations that need to continuously discover, research, qualify, and activate prospects at scale.”**

My original use case was recruiting and opportunity discovery, but the underlying system is domain-agnostic. The target profile can represent an ideal customer, candidate, partner, account, or any other prospect. 

By parameterizing what "relevance" means into structured search intelligence, semantic qualification gates, multi-tiered contact enrichment, and deep context synthesis, the engine transforms raw, unstructured web signals into verified, actionable prospect records with zero manual research overhead.

---

## 🏛️ End-to-End Architecture

```
                 TARGET PROFILE
                       │
                       ▼
               AI PROFILE PARSER
                       │
                       ▼
           ┌──────────────────────┐
           │  SEARCH INTELLIGENCE │
           │                      │
           │ Query generation     │
           │ Search strategies    │
           │ Platform discovery   │
           └──────────┬───────────┘
                      │
                      ▼
               PROSPECT DISCOVERY
                      │
                      ▼
              WEB INTELLIGENCE
                      │
               ┌──────┴──────┐
               ▼             ▼
           Company/       People/
           Entity data    Contact data
               │             │
               └──────┬──────┘
                      ▼
               AI QUALIFICATION
                      │
                 Score / Fit
                      │
               ┌──────┴──────┐
               │             │
            Reject        Qualified
                             │
                             ▼
                      ENRICHMENT
                             │
                             ▼
                   CONTEXT SYNTHESIS
                             │
                             ▼
                  PERSONALIZED OUTREACH
                             │
                             ▼
                  CRM / SHEETS / EMAIL
```

---

## 🌐 Where This System Can Be Used

```
                    LEAD INTELLIGENCE ENGINE
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
       SALES              RECRUITING        PARTNERSHIPS
          │                   │                   │
   Find ICP accounts    Find candidates     Find strategic
   + decision makers   + hiring signals      partners
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
                              ▼
                         OTHER USE CASES
                              │
                  ┌───────────┼───────────┐
                  ▼           ▼           ▼
                MARKET      INVESTOR     AGENCY
              INTELLIGENCE  RESEARCH    PROSPECTING
```

> **The Key Architectural Abstraction:**
> 
> *The core engine doesn't care whether you are looking for a customer, candidate, partner, or another type of prospect. The target profile defines what relevance means.*

---

## 🏢 Concrete Enterprise Applications

Rather than being a single-purpose script, the platform functions as an extensible intelligence pipeline for diverse business functions:

### 1. B2B Sales & Go-To-Market (GTM)
* **The Problem:** Sales and SDR teams spend an enormous amount of time manually identifying target accounts, researching company signals, finding verified decision-makers, and crafting personalized outreach.
* **The Pipeline Flow:**
  ```
  ICP Definition
       ↓
  Discover Target Companies
       ↓
  Research Company Signals
       ↓
  Identify Decision-Makers
       ↓
  Score Account Fit
       ↓
  Enrich Contacts (Email / LinkedIn)
       ↓
  Generate Personalized Outreach
  ```

### 2. Talent Acquisition & Recruiting
* **The Problem:** Sourcing teams struggle to find specialized talent matching nuanced skillsets and culture criteria across fragmented web ecosystems.
* **The Solution:** *The same architecture runs in reverse for recruiting teams.*
* **The Pipeline Flow:**
  ```
  Hiring Profile
       ↓
  Discover Relevant Candidates & Portfolios
       ↓
  Analyze Experience & Repositories
       ↓
  Score Technical & Cultural Fit
       ↓
  Resolve Verified Contact Channels
       ↓
  Personalized Recruiter Outreach
  ```

### 3. Strategic Partnerships & Business Development
* **The Problem:** Identifying ecosystem partners, complementary platforms, and channel alliances requires scanning across diverse verticals.
* **Example:** An enterprise launching an AI infrastructure product can define a partner profile to continuously discover complementary SaaS platforms, systems integrators, digital agencies, or co-selling partners.
* **The Insight:** *Same engine. Different target profile.*

### 4. Continuous Market Intelligence & Competitive Tracking
* **The Problem:** Market intelligence is often point-in-time and goes stale quickly.
* **The Solution:** Leveraging automated scheduling (e.g., GitHub Actions / CI cron triggers), enterprises can continuously monitor market segments for funding announcements, new product releases, leadership changes, tech stack migrations, and hiring surges.

### 5. Multi-Client Agency Prospecting
* **The Problem:** Lead generation agencies traditionally build bespoke scrapers and workflows for each client engagement.
* **The Architecture:** With isolated, declarative target profiles, an agency can run parallel prospecting engines without rewriting underlying infrastructure:
  ```
  Client A ICP  ──►  Pipeline A (B2B SaaS Founders)
  Client B ICP  ──►  Pipeline B (FinTech Heads of Growth)
  Client C ICP  ──►  Pipeline C (Healthcare Procurement)
  ```

---

## 💡 The Enterprise Value Proposition

The value isn't simply generating more leads. It is **reducing the massive amount of manual research and fragmented tooling** required between identifying a potential lead and having a qualified, actionable record ready for engagement.

```
                    TRADITIONAL WORKFLOW
Discovery ──► Research ──► Qualification ──► Enrichment ──► Writing
    │             │              │               │             │
  Manual        Manual         Manual          Manual        Manual
    │             │              │               │             │
    ▼             ▼              ▼               ▼             ▼
               High Latency • Inconsistent Context • Tool Sprawl


                 AUTONOMOUS INTELLIGENCE ENGINE
                                │
                         AI + Automation
                                │
                  Discovery ──► Qualification
                                │
                            Enrichment
                                │
                        Context Synthesis
                                │
                         Outreach Draft
```

---

## 🌟 Key System Capabilities

- **🌐 Search Intelligence & Multi-Channel Dorking**: Dynamically compiles declarative target profiles into 30–50 structured discovery queries and site-dorks across global registries, VC portfolios (Peak XV, Blume, Antler), regional hubs (EU-Startups, Inc42, Magnitt, TokyoDev), remote platforms (Wellfound, Himalayas, Arc.dev), and social feeds (LinkedIn/X dorks).
- **⚡ Resilient Web Intelligence Layer**: Built on [Scrapling](https://github.com/D4V130/Scrapling) with fast plain-HTTP requests and automated stealth Chromium fallback for client-rendered Single Page Applications (SPAs).
- **🧠 AI Semantic Qualification Gate**: Uses Google Gemini (`gemini-3.6-flash` Primary) or Groq (`qwen/qwen3.6-27b`) to score criteria fit (0–100) and generate rationale before committing downstream enrichment resources.
- **🔍 Multi-Tier Contact Enrichment**: Cascading 4-tier contact resolution:
  - **Tier 0**: Public website email discovery (zero cost / immediate acceptance).
  - **Tier 1a**: Apollo.io Web Session API (`APOLLO_COOKIE`) for up to 10,000 free reveals/year.
  - **Tier 1b**: Apollo.io REST API (`APOLLO_API_KEY`) for direct contact lookups.
  - **Tier 2 & 3**: Personal pattern generation (`{first}.{last}@domain`) and generic mailbox probing with single-session SMTP `RCPT TO` verification, catch-all probe detection, and anti-enumeration host protection.
- **🛡️ Production Hardening & Concurrency**: SQLite with Write-Ahead Logging (`WAL` mode), busy timeouts, retry decorators with exponential backoff + jitter for all LLM API calls, and automated suppression list / bounce management.
- **✉️ Context-Aware Outreach Synthesis**: Non-templated, hyper-personalized outreach referencing recent company milestones, funding signals, and specific value propositions (< 120 words).
- **📥 Direct Delivery & Sync**: Integrated OAuth2 Google Sheets sync (`sheets_push.py`) and Gmail API draft creation / automated sending (`send_gmail.py`).

---

## 🛠️ Modular Pipeline Stages

| Stage | Script | Purpose |
|---|---|---|
| **0. Profile Analysis** | `resume_profile.py` | Extracts target profile parameters & domain context from documents or JSON |
| **0.5 Search Intelligence** | `query_gen.py` & `discovery_sources.py` | Generates 30–50 targeted queries & deterministic platform dorks |
| **1a. Prospect Discovery** | `discover_startups.py` | Runs multi-channel web searches and parses unstructured data into structured prospect entries |
| **1b. Web Intelligence** | `scrape_company_page.py` | Crawls corporate career/team pages for entity data, team contacts, and public emails |
| **2. AI Qualification** | `qualify.py` | Evaluates prospect fit (0–100 score + match rationale) via LLM reasoning |
| **3. Contact Enrichment** | `enrich_email.py` | Resolves target decision-maker names and validates email addresses across 4 tiers |
| **4. Context Synthesis & Pitch** | `draft_email.py` | Writes tailored outreach emails grounded in live entity signals and target context |
| **5. Delivery & Export** | `send_gmail.py` & `sheets_push.py` | Creates Gmail drafts / delivers emails and syncs multi-tab reports to Google Sheets |

---

## 🚀 Quickstart Guide

### 1. Installation & Environment Setup

```bash
git clone https://github.com/anchaltiwaryy/lead-gen-pipeline.git
cd lead-gen-pipeline

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies & Playwright browsers
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Credentials

Copy `.env.example` to `.env` and populate your API keys:

```bash
cp .env.example .env
```

```env
ACTIVE_PROFILE=gtm_devrel
YOUR_NAME="Your Name"
YOUR_ONE_LINER="Full-stack AI Engineer building autonomous lead engines."

# AI Providers
PRIMARY_AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.6-flash
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=qwen/qwen3.6-27b

# Enrichment (Optional Apollo Session / API)
APOLLO_COOKIE=
APOLLO_API_KEY=

# Pipeline Controls
AUTO_SEND=false
FIT_SCORE_THRESHOLD=50
```

---

## 🎮 Execution & CLI Commands

### Run Full Autonomous Pipeline
```bash
python main.py
```

### Run Stage-Specific Actions
```bash
# Discovery & web intelligence only
python main.py --scrape-only

# AI Qualification only
python main.py --qualify-only

# Contact Enrichment only
python main.py --enrich-only

# Run Automated Test Suite
pytest tests
```

### Export & Sync Analytics
```bash
# Export CSV analytical reports to exports/
python export_results.py

# Push exports directly to Google Sheets
python sheets_push.py
```

---

## 🗺️ Roadmap & Ongoing Architecture Upgrades

The platform is continuously evolving into a fully autonomous, enterprise-grade multi-agent fleet. The following enhancements are currently in development / rollout:

### 1. 🤖 Autonomous Multi-Agent Worker Fleet
- **Modular Typed Agents**: Replacing monolithic stage scripts with decoupled, Pydantic-typed Python agents (`DiscoveryAgent`, `WebIntelAgent`, `QualificationAgent`, `EnrichmentAgent`, `PitchSynthesisAgent`, `BrowserAgent`).
- **Deterministic Retries & Failure Boundaries**: Resilient execution with backoff jitter and automatic fallback between Groq (`llama-3.3-70b-versatile`) and Gemini (`gemini-2.5-flash`).

### 2. ⚡ Tiered Cache-Aside Engine (`cache.py`)
- **Upstash Redis + Local SQLite Fallback**: Sub-2ms distributed caching for LLM prompt/response pairs (14-day TTL), scraped web HTML (7-day TTL), and SMTP MX deliverability (30-day TTL).
- **Cost & Quota Protection**: Prevents redundant API calls and shields IP reputation during high-frequency crawl runs.

### 3. 🔒 Local-First Privacy & Cloudflare R2 Zero-Leak Sync
- **Zero Git Leaks**: Completely isolates private prospect data and contact records from open-source repositories (`leads.db` in `.gitignore`).
- **Serverless Cloud Snapshots**: Seamless pre-run pull and post-run push of encrypted database state to Cloudflare R2 object storage (10GB free tier, $0 egress fees).

### 4. 🖥️ Next.js 14 Control Center UI (`dashboard/`)
- **Real-Time Kanban & Funnel Analytics**: Interactive status board tracking lead progression from Discovery $\rightarrow$ Qualified $\rightarrow$ Enriched $\rightarrow$ Drafted $\rightarrow$ Sent/Applied $\rightarrow$ Replied.
- **1-Click Outreach Copilot**: Zero-ban-risk 1-click actions:
  - **Gmail**: Pre-fills drafts with hyper-personalized copy.
  - **LinkedIn & X**: Opens profiles and auto-copies tailored 280-char connection notes.
- **Live SSE Log Streaming**: Real-time worker activity monitor and stage triggers.

### 5. 🌐 Agentic In-Browser Portal Automation (`browser_agent.py`)
- **Persistent Authenticated Sessions**: Playwright-driven persistent storage states (`storage_state.json`) for portal interactions (e.g. Wellfound).
- **Humanized Anti-Detection Telemetry**: Realistic typing jitter (40–120ms/key) and randomized delays (5–15s) for automated application modal handling.

---

## 📄 License

MIT License — free for personal and commercial use.