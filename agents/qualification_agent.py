"""Agent 3 - AI Qualification Gate.

Semantic scoring of company signals, tech stack, and role fit against the
active target profile using structured Pydantic JSON output. Leads below
FIT_SCORE_THRESHOLD are marked `skipped`, preventing expensive downstream
enrichment calls on bad fits.
"""
from __future__ import annotations

import json
from typing import Optional

from pydantic import BaseModel, Field, ValidationError

from cache import cached_llm
from config import (
    GEMINI_API_KEY,
    GROQ_API_KEY,
    GROQ_MODEL,
    FIT_SCORE_THRESHOLD,
    QUALIFY_BATCH_LIMIT,
)
from db import get_conn, get_leads_by_status, update_lead
from logger import log
from resume_profile import load_profile


class FitScore(BaseModel):
    """Structured qualification output enforced by Pydantic."""

    fit_score: int = Field(ge=0, le=100, description="0-100 semantic fit score")
    reason: str = Field(min_length=1, description="One-sentence rationale")

    @property
    def passes(self) -> bool:
        return self.fit_score >= FIT_SCORE_THRESHOLD


PROMPT = """Evaluate how well this job posting matches the candidate based on these specific rules:

SCORING RULES (Return fit_score 0-100):
1. Location/Work Type: Strongly prefer Remote (Global, Worldwide, or India-friendly). Give high scores (80-100) if remote; penalize heavily if strictly on-site in a non-India location without relocation support.
2. Experience Level: Target 0-3 years of experience (early career, entry-level, junior, or intern).
3. Role Type Preference: Prefer Internship roles FIRST, followed by Full-time entry/junior roles.
4. Skill/Profile Match: Match role duties & skills against candidate profile. Be generous with adjacent/transferable AI, Full-stack, DevRel, or GTM skills.

Return ONLY valid JSON with keys "fit_score" (integer 0-100) and "reason" (one sentence explaining the score):
{{"fit_score": 75, "reason": "Remote intern role matching candidate AI/full-stack skills with 0-3 yrs YOE requirements."}}

Candidate profile: {profile}
Company: {company}
Role/posting: {posting}
"""


class QualificationAgent:
    """Scores 'new' leads and gates them to 'qualified' or 'skipped'."""

    name = "qualification"

    def __init__(self, threshold: int = FIT_SCORE_THRESHOLD,
                 limit: int = QUALIFY_BATCH_LIMIT,
                 profile: Optional[dict] = None):
        self.threshold = threshold
        self.limit = limit
        self.profile = profile or load_profile()

    @cached_llm()
    def score(self, company: str, posting_text: str, profile: dict) -> FitScore:
        """Structured LLM scoring with 14-day prompt cache. Returns FitScore."""
        prompt = PROMPT.format(
            profile=json.dumps(profile),
            company=company,
            posting=(posting_text or "")[:4000],
        )
        raw = None
        if GEMINI_API_KEY:
            try:
                from google import genai
                from config import GEMINI_MODEL
                client = genai.Client(api_key=GEMINI_API_KEY)
                response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
                raw = response.text.strip().strip("```json").strip("```").strip()
            except Exception as e:
                log.warning(f"[qualify] Gemini scoring failed ({e}); falling back to Groq...")

        if not raw and GROQ_API_KEY:
            try:
                from groq import Groq
                client = Groq(api_key=GROQ_API_KEY)
                completion = client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a recruiter evaluating candidate job fit. Output valid JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                raw = completion.choices[0].message.content
            except Exception as e:
                log.error(f"[qualify] Groq fallback also failed ({e})")

        if not raw:
            raise ValueError("No AI response obtained from configured providers")
        return FitScore.model_validate_json(raw)

    def run(self, limit: Optional[int] = None) -> int:
        conn = get_conn()
        leads = get_leads_by_status(conn, "new", limit=limit or self.limit)
        processed = 0
        for lead in leads:
            posting = (lead.get("posting_text") or "").strip()
            if not posting:
                # Fallback to role_title, company_context, funding, and region
                role = lead.get("role_title") or ""
                ctx = lead.get("company_context") or ""
                fund = lead.get("funding_info") or ""
                if role or ctx:
                    posting = f"Role: {role}\nCompany Context: {ctx}\nFunding: {fund}\nRegion: {lead.get('region') or ''}"
                else:
                    continue
            try:
                score = self.score(lead["company"], posting, self.profile)
            except ValidationError as e:
                log.error(f"[qualify] schema validation failed for {lead['company']}: {e}")
                continue
            except Exception as e:
                log.error(f"[qualify] failed for {lead['company']}: {e}")
                continue
            status = "qualified" if score.passes else "skipped"
            update_lead(
                conn,
                lead["id"],
                fit_score=score.fit_score,
                fit_reason=score.reason,
                status=status,
            )
            processed += 1
        conn.close()
        log.info(f"[qualify] scored {processed} leads; threshold {self.threshold}")
        return processed

    def __repr__(self) -> str:
        return f"<QualificationAgent threshold={self.threshold}>"