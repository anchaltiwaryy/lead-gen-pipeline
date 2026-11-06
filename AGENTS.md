# AGENTS.md — Autonomous Lead Intelligence Engine & Multi-Agent Platform

Architecture, design guidelines, and operational runbook for AI agents and developers working on this codebase.

---

## 🎯 System Mission & Scope

An enterprise-grade, autonomous lead intelligence platform that continuously discovers, qualifies, enriches, and activates high-value prospect records across arbitrary domains (B2B Sales / ICP accounts, Talent Acquisition, Strategic Partnerships, and Continuous Market Intelligence).

---

## 🏛️ End-to-End Multi-Agent Architecture

```
                               ┌──────────────────────────────────────────────────┐
                               │           Next.js 14 Web Dashboard UI            │
                               │  - Lead Kanban & Status Management (Review/Edit) │
                               │  - 1-Click LinkedIn & X Connection Copilot       │
                               │  - Live Funnel Analytics & Execution Triggers    │
                               └────────────────────────┬─────────────────────────┘
                                                        │ REST / SSE
                                                        ▼
                               ┌──────────────────────────────────────────────────┐
                               │            FastAPI Orchestration Layer           │
                               └──────────┬─────────────────────────────┬─────────┘
                                          │                             │
                                          ▼                             ▼
               ┌──────────────────────────────────────┐     ┌───────────────────────────────────┐
               │    Tiered Cache Engine (`cache.py`)  │     │    Local-First Storage Layer      │
               │ - Upstash Redis / Redis Cloud Layer  │     │ - SQLite (WAL Mode, < 1ms query)  │
               │ - Local SQLite `kv_cache` Fallback   │     │ - Cloudflare R2 Zero-Leak Sync    │
               │ - LLM / Scrape / SMTP TTL Shields    │     │ - Zero Lead Data in Git Repo      │
               └──────────────────┬───────────────────┘     └───────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 Autonomous Multi-Agent Worker Fleet                                    │
│                                                                                                        │
│  ┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐  ┌──────────────────┐  │
│  │ 1. Discovery Agent   │   │ 2. Web Intel Agent   │   │ 3. Qualification     │  │ 4. Enrichment    │  │
│  │ Dorks, Wellfound, VC │──►│ Fast HTTP + Stealth  │──►│ LLM Semantic Scoring │─►│ Apollo + SMTP    │  │
│  │ Portfolios, News RSS │   │ Chromium Headless    │   │ & Fit Reasoning Gate │  │ Cascading Tiers  │  │
│  └──────────────────────┘   └──────────────────────┘   └──────────────────────┘  └──────────────────┘  │
│                                                                                            │           │
│                                                                                            ▼           │
│  ┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐  ┌──────────────────┐  │
│  │ 8. Delivery Engine   │   │ 7. Browser Agent     │   │ 6. Copilot Action    │  │ 5. Pitch Agent   │  │
│  │ Fixed Gmail Drafts   │◄──│ Wellfound Auto-Apply │◄──│ 1-Click LinkedIn & X │◄─│ Hyper-Tailored   │  │
│  │ & Sheets Atomic Sync │   │ Humanized Jitter & UI│   │ Connection Generator │  │ Multi-Format Copy│  │
│  └──────────────────────┘   └──────────────────────┘   └──────────────────────┘  └──────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔒 Storage & Privacy Architecture (Local-First + Cloudflare R2)

To maintain 100% privacy on open-source repositories and prevent repository bloat, the system decouples source code from lead data:

```
[ Local Worker Execution ] ──► SQLite `leads.db` (WAL Mode, Sub-1ms I/O)
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
        [ Pre-Run Pull ]                       [ Post-Run Push ]
    Pull encrypted snapshot from           Push updated snapshot to
    Cloudflare R2 Bucket (Private)         Cloudflare R2 Bucket (Private)
```

- **Zero Git Leaks**: `leads.db` is strictly in `.gitignore`.
- **Zero Network Latency**: Crawling and qualification loops execute against local disk without remote DB round-trip delays.
- **Serverless Cloud Backup**: `sync_r2.py` syncs state between GitHub Actions / local environments using Cloudflare R2 (10GB free, $0 egress fees).

---

## ⚡ Tiered Cache-Aside Engine (`cache.py`)

Protects LLM token quotas, prevents duplicate website scrapes, and shields SMTP IP reputation:

```
Request ──► Redis Cache (Upstash / Local) ──► Hit: Return immediately (< 2ms)
                   │
                   ▼ (Miss or Redis Offline)
            SQLite `kv_cache` ─────────────► Hit: Return cached record (< 1ms)
                   │
                   ▼ (Miss)
            Execute Live API / Crawl ──────► Write to Redis & SQLite
```

### Cache Retention Policies:
- **LLM Prompt / Response**: 14-day TTL (keyed on `sha256(system_prompt + user_prompt)`).
- **Web Domain Scrapes**: 7-day TTL (keyed on `domain_hash`).
- **SMTP Domain Deliverability**: 30-day TTL (keyed on `mx_host`).

---

## 🤖 Specialized Agent Specifications

### 1. Discovery Agent (`agents/discovery_agent.py`)
- **Responsibility**: Translates declarative target profiles into structured search strategies and crawls unauthenticated feeds.
- **Data Sources**:
  - DuckDuckGo News API & Google Dorks (`site:linkedin.com/in/`, `site:x.com`).
  - VC Portfolios (Peak XV, Blume Ventures, Antler, Y Combinator).
  - Startup directories (EU-Startups, Inc42, Magnitt, TokyoDev, Wellfound public listings).
- **Output**: Generates raw candidate entities with company name, domain, funding signals, and role information.

### 2. Web Intelligence Agent (`agents/web_intel_agent.py`)
- **Responsibility**: Deep crawls target entity domains using [Scrapling](https://github.com/D4V130/Scrapling).
- **Execution**:
  - Attempts high-speed plain HTTP requests first.
  - Automatically falls back to stealth headless Chromium when JavaScript rendering or client SPAs are detected.
  - Extracts full careers text, team members, public email mailboxes, and founder links.
- **Cache**: Checks domain cache before initiating outbound requests (7-day TTL).

### 3. AI Qualification Gate (`agents/qualification_agent.py`)
- **Responsibility**: Semantic evaluation of company signals, tech stack, and role fit against the active target profile.
- **Model Layer**: Google Gemini (`gemini-3.6-flash` Primary) with automatic fallback to Groq (`qwen/qwen3.6-27b`) via structured JSON/Pydantic schemas.
- **Gate Logic**:
  - Scores fit (0–100) and produces explicit `fit_reason`.
  - Resilient qualification fallback: Evaluates `role_title`, `company_context`, and `funding_info` when raw `/careers` page scraping is unavailable.
  - Leads scoring below threshold (`FIT_SCORE_THRESHOLD=50`) are marked `skipped`, preventing expensive downstream enrichment calls.

### 4. Multi-Tier Contact Enrichment Agent (`agents/enrichment_agent.py`)
- **Cascading Resolution**:
  - **Tier 0**: Free public website emails found during scraping.
  - **Tier 1a**: Apollo.io Web Session API (`APOLLO_COOKIE`) for free reveals.
  - **Tier 1b**: Apollo.io REST API (`APOLLO_API_KEY`).
  - **Tier 2 & 3**: Pattern generation (`{first}.{last}@{domain}`) + single-session SMTP `RCPT TO` verification with anti-catchall detection.
- **Suppression**: Auto-verifies against `suppression_list` table to prevent re-contacting bounced or opted-out domains.

### 5. Multi-Format Pitch Synthesis Agent (`agents/pitch_agent.py`)
- **Responsibility**: Generates 3 distinct personalized outreach formats per qualified lead:
  1. **Founder Cold Email**: < 120 words, hyper-grounded in specific company milestones and value proposition.
  2. **LinkedIn Connection Note**: < 300 characters, high-context hook referencing specific technical/business alignment.
  3. **X (Twitter) DM / Hook**: Conversational, low-friction entry point.

### 6. Browser Automation Agent (`agents/browser_agent.py`)
- **Responsibility**: Handles authenticated portal actions (e.g. Wellfound, job boards) using persistent browser sessions.
- **Session Management**: Uses Playwright storage state (`wellfound_session.json` or real Chrome User Data profile).
- **Action Mode**:
  - `AUTO_APPLY=false` (Default / Copilot Mode): Fills modal with custom note and leaves for user review.
  - `AUTO_APPLY=true` (Autonomous Mode): Types custom note with human typing jitter (40–120ms/key), adds randomized delays (5–15s), and submits.

---

## 🛡️ Anti-Ban Protocol for LinkedIn & X

1. **Decoupled Discovery (0% Ban Risk)**: All lead discovery, company research, and founder identification is done via public Google X-Ray dorks and unauthenticated endpoints. Personal accounts are never used for mass scraping.
2. **Humanized In-Browser Limits**:
   - **LinkedIn Connection Requests**: Capped at 10–15 / day with 60–180s randomized intervals.
   - **X (Twitter) DMs**: Capped at 10–15 / day to open DMs only.
   - **Mouse & Typing Telemetry**: Uses realistic typing cadences and bezier curve mouse trajectories.
3. **1-Click Copilot Mode**: Recommended default where the AI drafts the copy, and the user executes the final send with 1 click.

---

## ✉️ Gmail Draft & Delivery Engine Overhaul

### Problem Diagnosis:
1. `send_gmail.py` was failing due to missing `token.json` and interactive auth attempts in background processes.
2. Draft messages were constructed via raw string templates instead of RFC-compliant `EmailMessage` objects, leading to UTF-8 encoding drops and missing MIME headers.

### Robust Implementation:
- **MIME Standard**: Uses `email.message.EmailMessage` with `utf-8` charset, setting explicit `To`, `Subject`, and `Content-Type: text/html`.
- **Standalone Bootstrapper**: `python auth_gmail.py` runs once interactively to generate `token.json`.
- **Idempotent Status Lifecycle**:
  ```
  enriched ──► draft_email.py ──► drafted (local file ready)
  drafted  ──► send_gmail.py  ──► draft_created (Gmail API Draft ID stored)
  draft_created ──► send / approve ──► sent (delivered)
  ```

---

## 🖥️ Next.js 14 Control Center & Dashboard

Located in `/dashboard`, the dashboard connects to the backend API (`api.py`) for complete visibility and manual override:

### Key Features:
1. **Pipeline Kanban & Status Funnel**:
   - Filter by status (`new`, `qualified`, `enriched`, `drafted`, `draft_created`, `sent`, `applied`, `replied`, `rejected`).
   - Fit score sliders and source filters (Wellfound, News, VC Portfolios, Dorks).
2. **Lead Inspection Drawer**:
   - Read scraped company context, live posting text, AI reasoning, and verified contact emails.
   - Edit draft emails and LinkedIn pitch notes on the fly.
3. **1-Click Outreach Copilot**:
   - **Gmail Button**: Opens Gmail compose or copies Gmail draft link.
   - **LinkedIn Button**: Opens founder LinkedIn profile and copies tailored 280-char note to clipboard.
   - **X Button**: Opens direct DM URL with pre-filled message.
4. **Live Execution Controls**:
   - Trigger single stages or full autonomous runs with real-time SSE log streaming.

---

## 🚀 Quick Reference Commands

```bash
# 1. Authorize Gmail API (one-time interactive login)
python auth_gmail.py

# 2. Authorize Wellfound Session (one-time interactive login)
python auth_wellfound.py

# 3. Sync Database with Cloudflare R2 (Optional Serverless Cloud Persistence)
python sync_r2.py pull
python sync_r2.py push

# 4. Start Backend API & Pipeline Workers
python api.py

# 5. Start Next.js Dashboard UI
cd dashboard && npm run dev

# 6. Run Full Autonomous Pipeline via CLI
python main.py
```
