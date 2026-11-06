"""Stage 2 - AI qualification gate with retry resilience and structured logging.

Runs on every 'new' lead BEFORE any enrichment call is spent. Scores fit
against resume_profile.json using the actual scraped posting_text.
"""
import json
from config import GEMINI_API_KEY, GROQ_API_KEY, GROQ_MODEL, FIT_SCORE_THRESHOLD, QUALIFY_BATCH_LIMIT
from db import get_conn, get_leads_by_status, update_lead
from resume_profile import load_profile
from retry_util import with_retry
from logger import log

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


@with_retry(max_retries=4)
def score_lead(lead: dict, profile: dict) -> dict:
    prompt = PROMPT.format(
        profile=json.dumps(profile),
        company=lead["company"],
        posting=lead.get("posting_text") or "",
    )
    if GEMINI_API_KEY:
        try:
            from google import genai
            from config import GEMINI_MODEL
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            text = response.text.strip().strip("```json").strip("```").strip()
            return json.loads(text)
        except Exception as e:
            log.warning(f"[qualify] Gemini failed ({e}); falling back to Groq...")

    if GROQ_API_KEY:
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
        return json.loads(completion.choices[0].message.content)
    raise ValueError("Neither GEMINI_API_KEY nor GROQ_API_KEY is configured in config.py")


def qualify_leads(limit: int = QUALIFY_BATCH_LIMIT) -> int:
    conn = get_conn()
    profile = load_profile()
    leads = get_leads_by_status(conn, "new", limit=limit)
    processed = 0
    for lead in leads:
        posting = (lead.get("posting_text") or "").strip()
        if not posting:
            role = lead.get("role_title") or ""
            ctx = lead.get("company_context") or ""
            fund = lead.get("funding_info") or ""
            if role or ctx:
                lead = dict(lead)
                lead["posting_text"] = f"Role: {role}\nCompany Context: {ctx}\nFunding: {fund}\nRegion: {lead.get('region') or ''}"
            else:
                continue
        try:
            result = score_lead(lead, profile)
            fit = int(result["fit_score"])
        except Exception as e:
            log.error(f"[qualify] failed for {lead['company']}: {e}")
            continue
        status = "qualified" if fit >= FIT_SCORE_THRESHOLD else "skipped"
        update_lead(
            conn,
            lead["id"],
            fit_score=fit,
            fit_reason=result.get("reason", ""),
            status=status,
        )
        processed += 1
    log.info(f"[qualify] scored {processed} leads; qualified >= {FIT_SCORE_THRESHOLD}.")
    return processed


if __name__ == "__main__":
    qualify_leads()