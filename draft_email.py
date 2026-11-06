"""Stage 4 - personalized outreach email generation with retry resilience and structured logging.

Uses the qualify-stage fit_reason so each email is grounded in an actual match.
"""
import os
import json
from config import GEMINI_API_KEY, GROQ_API_KEY, GROQ_MODEL, YOUR_NAME, YOUR_ONE_LINER, RESUME_LINK
from db import get_conn, get_leads_by_status, update_lead
from retry_util import with_retry
from logger import log

PROMPT = """Write a short, personalized cold outreach email from {name}.
Context that must be used, not invented:
- Candidate one-liner: {one_liner}
- Why this role fits (from earlier AI qualification): {fit_reason}
- Company: {company}
- Contact: {contact}
- Role / posting text: {posting}
- What the company does: {context}
- How we found them (signal): {signal}

Rules:
- Open with ONE specific line referencing the signal or company context (e.g. their
  recent funding round, a hiring signal, or what the company builds). Never fabricate.
- Two lines on how the candidate's strongest skills map to the role.
- One low-friction ask (15-minute intro/chat).
- "Resume: {resume_link}" near the end.
- Under 120 words. Plain text, no markdown headers, no emoji.

Return ONLY the email body (no subject, no quoting).
"""


@with_retry(max_retries=4)
def draft_email(company, contact_name, contact_title, posting_text, fit_reason,
                company_context="", source="") -> str:
    prompt = PROMPT.format(
        name=YOUR_NAME,
        one_liner=YOUR_ONE_LINER,
        fit_reason=fit_reason or "",
        company=company,
        contact=f"{contact_title or ''} {contact_name or ''}".strip(),
        posting=(posting_text or "")[:1500],
        context=company_context or "",
        signal=source or "",
        resume_link=RESUME_LINK,
    )
    if GEMINI_API_KEY:
        try:
            from google import genai
            from config import GEMINI_MODEL
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            return response.text.strip()
        except Exception as e:
            log.warning(f"[draft] Gemini generation failed ({e}); falling back to Groq...")

    if GROQ_API_KEY:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a professional outreach writer. Output plain email body only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        return completion.choices[0].message.content.strip()
    raise ValueError("Neither GEMINI_API_KEY nor GROQ_API_KEY is configured in config.py")


def draft_enriched(limit: int = 25) -> int:
    conn = get_conn()
    leads = get_leads_by_status(conn, "enriched", limit=limit)
    done = 0
    for lead in leads:
        body = draft_email(
            lead["company"],
            lead.get("contact_name") or "",
            lead.get("contact_title") or "",
            lead.get("posting_text") or "",
            lead.get("fit_reason") or "",
            company_context=lead.get("company_context") or "",
            source=lead.get("source") or "",
        )
        if not body:
            update_lead(conn, lead["id"], status="skipped")
            continue
        save_draft(lead, body)
        update_lead(conn, lead["id"], status="drafted")
        done += 1
    log.info(f"[draft] wrote {done} drafts.")
    return done


def save_draft(lead: dict, body: str) -> str:
    """Persist draft body to a plain text file for review."""
    os.makedirs("drafts", exist_ok=True)
    safe = "".join(c if c.isalnum() or c in " ._-" else "_" for c in lead["company"])
    path = os.path.join("drafts", f"{safe}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"To: {lead.get('email') or ''}\n")
        f.write(f"Company: {lead['company']}\n")
        f.write(f"Role: {lead.get('role_title') or ''}\n\n")
        f.write(body)
    return path


if __name__ == "__main__":
    draft_enriched()