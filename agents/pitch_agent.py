"""Agent 5 - Multi-Format Pitch Synthesis Agent.

Generates 3 distinct personalized outreach formats per qualified lead:
  1. Founder Cold Email   - < 120 words, hyper-grounded in company signals.
  2. LinkedIn Note        - < 300 chars, high-context hook.
  3. X (Twitter) DM/Hook  - conversational, low-friction entry point.

Pydantic enforces character limits & format compliance at the boundary.
"""
from __future__ import annotations

import json
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from cache import cached_llm
from config import GEMINI_API_KEY, GROQ_API_KEY, GROQ_MODEL, RESUME_LINK, YOUR_NAME, YOUR_ONE_LINER
from db import get_conn, get_leads_by_status, update_lead
from logger import log


class PitchBundle(BaseModel):
    """Structured multi-format outreach validated on construction."""

    email_body: str = Field(description="Cold email body (< 120 words)")
    linkedin_note: str = Field(description="LinkedIn connection note (< 300 chars)")
    x_dm: str = Field(description="X/Twitter DM hook (< 280 chars)")

    @field_validator("email_body")
    @classmethod
    def _email_words(cls, v: str) -> str:
        if len(v.split()) > 120:
            raise ValueError(f"Email exceeds 120 words ({len(v.split())})")
        return v

    @field_validator("linkedin_note")
    @classmethod
    def _linkedin_len(cls, v: str) -> str:
        if len(v) > 300:
            raise ValueError(f"LinkedIn note exceeds 300 chars ({len(v)})")
        return v

    @field_validator("x_dm")
    @classmethod
    def _x_len(cls, v: str) -> str:
        if len(v) > 280:
            raise ValueError(f"X DM exceeds 280 chars ({len(v)})")
        return v


PROMPT = """You are a professional outreach writer. Produce 3 outreach formats for a candidate.

Candidate: {name} - {one_liner} | Resume: {resume_link}
Company: {company} ({domain})
Contact: {contact}
Role / posting: {posting}
Company context: {context}
Signal (how we found them): {signal}
AI fit reasoning: {fit_reason}

Return ONLY valid JSON with exactly these keys:
{{
  "email_body": "cold email, under 120 words, opens with ONE specific line referencing the signal/context, 2 lines mapping skills to the role, one low-friction ask, ends with 'Resume: {resume_link}'. Plain text, no markdown, no emoji.",
  "linkedin_note": "connection note under 300 characters, high-context, references the signal",
  "x_dm": "X/Twitter DM hook under 280 characters, conversational and low-friction"
}}
"""


class PitchAgent:
    """Synthesizes and persists multi-format pitch copy for enriched leads."""

    name = "pitch"

    def __init__(self, limit: int = 25):
        self.limit = limit

    @cached_llm()
    def _llm_generate(self, system_prompt: str, user_prompt: str) -> str:
        if GEMINI_API_KEY:
            try:
                from google import genai
                from config import GEMINI_MODEL
                client = genai.Client(api_key=GEMINI_API_KEY)
                response = client.models.generate_content(model=GEMINI_MODEL, contents=user_prompt)
                return response.text.strip().strip("```json").strip("```").strip()
            except Exception as e:
                log.warning(f"[pitch] Gemini generation failed ({e}); falling back to Groq...")

        if GROQ_API_KEY:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            completion = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": user_prompt}],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            return completion.choices[0].message.content
        raise ValueError("Neither GEMINI_API_KEY nor GROQ_API_KEY is available")

    def generate(self, lead: dict) -> PitchBundle:
        user_prompt = PROMPT.format(
            name=YOUR_NAME,
            one_liner=YOUR_ONE_LINER,
            resume_link=RESUME_LINK,
            company=lead["company"],
            domain=lead.get("company_domain") or "",
            contact=f"{lead.get('contact_title') or ''} {lead.get('contact_name') or ''}".strip(),
            posting=(lead.get("posting_text") or "")[:1500],
            context=(lead.get("company_context") or "")[:800],
            signal=lead.get("source") or "",
            fit_reason=(lead.get("fit_reason") or "")[:600],
        )
        raw = self._llm_generate(
            "You are a professional outreach writer. Output valid JSON only.",
            user_prompt,
        )
        return PitchBundle.model_validate_json(raw)

    def run(self, limit: Optional[int] = None) -> int:
        conn = get_conn()
        leads = get_leads_by_status(conn, "enriched", limit=limit or self.limit)
        done = 0
        for lead in leads:
            try:
                bundle = self.generate(lead)
            except Exception as e:
                log.error(f"[pitch] generation failed for {lead['company']}: {e}")
                continue
            self.save(lead, bundle)
            update_lead(
                conn,
                lead["id"],
                draft_email_body=bundle.email_body,
                linkedin_note=bundle.linkedin_note,
                x_dm=bundle.x_dm,
                status="drafted",
            )
            done += 1
        conn.close()
        log.info(f"[pitch] wrote {done} multi-format pitches")
        return done

    @staticmethod
    def save(lead: dict, bundle: PitchBundle) -> str:
        """Persist the pitch bundle to a local text file for review."""
        import os
        os.makedirs("drafts", exist_ok=True)
        safe = "".join(c if c.isalnum() or c in " ._-" else "_" for c in lead["company"])
        path = os.path.join("drafts", f"{safe}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"To: {lead.get('email') or ''}\n")
            f.write(f"Company: {lead['company']}\n")
            f.write(f"Role: {lead.get('role_title') or ''}\n\n")
            f.write(bundle.email_body)
        with open(os.path.join("drafts", f"{safe}.linkedin.txt"), "w", encoding="utf-8") as f:
            f.write(bundle.linkedin_note)
        with open(os.path.join("drafts", f"{safe}.x.txt"), "w", encoding="utf-8") as f:
            f.write(bundle.x_dm)
        return path

    def __repr__(self) -> str:
        return f"<PitchAgent limit={self.limit}>"