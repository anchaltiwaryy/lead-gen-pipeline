"""Stage 0.5 - generate targeted search queries for startup discovery.

Uses the candidate profile + config to generate DuckDuckGo search queries
that find recently funded early-stage startups across all target regions.
"""
import json
from config import (
    GEMINI_API_KEY, GROQ_API_KEY, GROQ_MODEL,
    TARGET_ROLES, TARGET_REGIONS, STARTUP_STAGES,
    PREFERRED_REGIONS, FUNDING_RECENCY_MONTHS,
)
from resume_profile import load_profile

PROMPT = """You are a startup discovery assistant. Generate search queries to find
RECENTLY FUNDED or currently HIRING early-stage startups (Seed / Series A /
Series B) that are a real match for this candidate's profile.

Return ONLY valid JSON with these keys:

{{
  "funding_queries": [...],
  "hiring_queries": [...]
}}

funding_queries:  15-20 queries for funding news, deal trackers, and VC portfolios.
  Include search terms and site-dorks for sources like:
  - Global: TechCrunch, VentureBeat, Crunchbase, PitchBook, Topstartups.io, Startups.gallery
  - Europe/UK: EU-Startups, Otta, The Hub, WorkInStartups, NoFluffJobs, JustJoin.it
  - India: Inc42 DataLabs, Entrackr, YourStory, Tracxn, Startup India Portal
  - MENA: Magnitt, eFinancialCareers, GrabJobs UAE, Bayt
  - Japan: TokyoDev, Japan Dev
  - VC Portfolios: Peak XV, Blume Ventures, Elevation Capital, Accel India, Antler

hiring_queries:  15-20 queries surfacing actual JOB postings, niche job boards, and social hiring dorks:
  - Niche & Remote boards: Wellfound, Himalayas.app, WeWorkRemotely, Remotive, Arc.dev, RealWorkFromAnywhere
  - India boards: Cutshort, Instahyre, Cuvette, Unstop
  - LinkedIn/X Dorks:
    - site:linkedin.com/posts ("hiring" OR "looking for") ("remote" OR "work from home") ("intern" OR "founding engineer")
    - ("DM open" OR "looking for intern" OR "hiring remote") ("AI" OR "Full Stack" OR "DevRel")
  - Career sites: "site:*.jobs OR site:*.pinpoint OR careers {target_roles} startup"

RULES:
- Target SMALL to MID-SIZED startups only (under 500 employees)
- Cover ALL these regions: {regions}
- Target these funding stages: {stages}
- Mix sectors: AI, SaaS, fintech, devtools, health, e-commerce, B2B
- Hiring queries MUST reference the actual target roles: {target_roles}
- Recent funding = last {recency} months
- Diversity across regions, specific platform sources, and phrasings is essential.

Candidate profile: {profile}
"""


def generate_queries() -> dict:
    profile = load_profile()
    prompt = PROMPT.format(
        profile=json.dumps(profile),
        target_roles=", ".join(TARGET_ROLES),
        regions=", ".join(TARGET_REGIONS),
        stages=", ".join(STARTUP_STAGES),
        recency=FUNDING_RECENCY_MONTHS,
    )
    if GEMINI_API_KEY:
        try:
            from google import genai
            from config import GEMINI_MODEL
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            text = response.text.strip().strip("```json").strip("```").strip()
            base = json.loads(text)
            return base
        except Exception as e:
            log.warning(f"[query_gen] Gemini failed ({e}); falling back to Groq...")

    if GROQ_API_KEY:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a startup discovery assistant. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        base = json.loads(completion.choices[0].message.content)
        return base
    raise ValueError("Neither GEMINI_API_KEY nor GROQ_API_KEY is configured in config.py")

    # Append the deterministic job-board/social dork layer (no LLM needed).
    # This executes implementation_plan.md's "Target Platforms & Discovery
    # Sources Roadmap": careers boards + LinkedIn/X dorks become lead sources.
    from discovery_sources import build_source_queries
    base.setdefault("source_queries", [])
    base["source_queries"].extend(build_source_queries(TARGET_ROLES, TARGET_REGIONS))
    return base


if __name__ == "__main__":
    queries = generate_queries()
    print(json.dumps(queries, indent=2))
    total = sum(len(v) for v in queries.values() if isinstance(v, list))
    print(f"\nTotal queries generated: {total}")