"""Stage 0 - parse the resume once into a structured JSON profile.

Run once (or whenever the resume changes). The output (resume_profile.json) is
reused by query_gen, qualify, and draft so the PDF is not re-parsed every run.
"""
import json
import os
from config import GEMINI_API_KEY, GROQ_API_KEY, GROQ_MODEL, RESUME_PATH, PROFILE_JSON_PATH

PROMPT = """Extract a structured profile from this resume for job-matching purposes.
Return ONLY valid JSON with keys:
- "core_skills": list of 8-12 technical skills, most relevant first
- "experience_level": one of "intern" | "junior" | "mid" | "senior"
- "role_titles": list of 5-8 job titles this person is a realistic fit for
- "domain_strengths": list of 3-5 domains/industries they have real project experience in
- "notable_projects": list of 2-4 one-line project highlights (for use in outreach emails)

Resume Content:
{resume_text}
"""

PROFILE_PATH = PROFILE_JSON_PATH


def _clean_json(text: str) -> str:
    return text.strip().strip("```json").strip("```").strip()


def _extract_pdf_text(path: str) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"[profile] pypdf extraction warning: {e}")
        return ""


def build_resume_profile(path: str = RESUME_PATH) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Resume not found at {path}")

    if GROQ_API_KEY:
        resume_text = _extract_pdf_text(path)
        if not resume_text:
            raise ValueError(f"Could not extract text from PDF at {path} for Groq processing.")
    if GEMINI_API_KEY:
        try:
            from google import genai
            from config import GEMINI_MODEL
            client = genai.Client(api_key=GEMINI_API_KEY)
            resume_text = _extract_pdf_text(path)
            if resume_text:
                prompt = PROMPT.format(resume_text=resume_text)
                response = client.models.generate_content(
                    model=GEMINI_MODEL, contents=prompt
                )
            else:
                file = client.files.upload(file=path)
                prompt = PROMPT.format(resume_text="See attached PDF file.")
                response = client.models.generate_content(
                    model=GEMINI_MODEL, contents=[prompt, file]
                )
            profile = json.loads(_clean_json(response.text))
        except Exception:
            profile = None

    if not profile and GROQ_API_KEY:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        prompt = PROMPT.format(resume_text=resume_text)
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a resume parser. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        profile = json.loads(completion.choices[0].message.content)
    
    if not profile:
        raise ValueError("Neither GEMINI_API_KEY nor GROQ_API_KEY produced a valid profile")

    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)
    return profile


def load_profile(path: str = PROFILE_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    print(json.dumps(build_resume_profile(), indent=2))