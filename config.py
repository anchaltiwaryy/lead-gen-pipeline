"""Configuration.

Secrets (API keys) are read from environment variables or an optional local
`.env` file (git-ignored). NEVER hardcode real keys in this file; track
.env.example instead.
"""
import os
from dotenv import load_dotenv

load_dotenv()  # reads ./.env if present

# Active profile toggle: 'engineering' or 'gtm_devrel'
ACTIVE_PROFILE = os.getenv("ACTIVE_PROFILE", "gtm_devrel")

PROFILES = {
    "engineering": {
        "resume_path": os.getenv("RESUME_PATH_ENGINEERING", "Resume_Engineering_Technical.pdf"),
        "resume_link": os.getenv(
            "RESUME_LINK_ENGINEERING",
            "https://example.com/resume_engineering.pdf",
        ),
        "profile_json": "resume_profile.json",
        "target_roles": os.getenv(
            "TARGET_ROLES_ENGINEERING",
            ["AI engineer", "full-stack engineer", "software engineer intern", "AI product engineer", "ML engineer"],
        ),
    },
    "gtm_devrel": {
        "resume_path": os.getenv("RESUME_PATH_GTM", "Resume_GTM_DevRel.pdf"),
        "resume_link": os.getenv(
            "RESUME_LINK_GTM",
            "https://example.com/resume_gtm.pdf",
        ),
        "profile_json": "resume_profile_gtm.json",
        "target_roles": [
            "Developer Advocate", "DevRel Engineer", "Technical Growth Engineer",
            "GTM Engineer", "Solutions Architect",
        ],
    },
}

RESUME_PATH = PROFILES[ACTIVE_PROFILE]["resume_path"]
RESUME_LINK = PROFILES[ACTIVE_PROFILE]["resume_link"]
PROFILE_JSON_PATH = PROFILES[ACTIVE_PROFILE]["profile_json"]
TARGET_ROLES = PROFILES[ACTIVE_PROFILE]["target_roles"]

YOUR_NAME = os.getenv("YOUR_NAME", "Your Name")
YOUR_ONE_LINER = os.getenv(
    "YOUR_ONE_LINER",
    "Full-stack AI product engineer — building end-to-end AI products and lead engines."
)

# --- Discovery settings ---
TARGET_REGIONS = [
    "Europe", "US", "UK", "Australia", "Japan", "Canada",
    "Netherlands", "India", "Dubai", "Singapore", "Germany",
    "France", "Israel", "Southeast Asia",
]
STARTUP_STAGES = ["Pre-Seed", "Seed", "Series A", "Series B"]
MAX_EMPLOYEES = int(os.getenv("MAX_EMPLOYEES", "500"))
FUNDING_RECENCY_MONTHS = int(os.getenv("FUNDING_RECENCY_MONTHS", "12"))
DISCOVERY_QUERIES_PER_RUN = int(os.getenv("DISCOVERY_QUERIES_PER_RUN", "40"))

PREFERRED_REGIONS = ["Remote", "Worldwide", "US", "EU", "India"]
PAY_MIN_USD_MONTHLY = {"internship": 500, "fulltime": 2500}
DAILY_TARGET = 100
FIT_SCORE_THRESHOLD = int(os.getenv("FIT_SCORE_THRESHOLD", "50"))
DB_PATH = os.getenv("DB_PATH", "leads.db")
AUTO_SEND = os.getenv("AUTO_SEND", "false").lower() == "true"
MAX_ACTIONS_PER_RUN = int(os.getenv("MAX_ACTIONS_PER_RUN", "25"))

# --- AI credentials (from .env / env) ---
PRIMARY_AI_PROVIDER = os.getenv("PRIMARY_AI_PROVIDER", "gemini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.6-27b")
GROQ_CRAWL_MODEL = os.getenv("GROQ_CRAWL_MODEL", "qwen/qwen3.6-27b")
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")
APOLLO_COOKIE = os.getenv("APOLLO_COOKIE", "")
APOLLO_CSRF_TOKEN = os.getenv("APOLLO_CSRF_TOKEN", "")
APOLLO_APP_TOKEN = os.getenv("APOLLO_APP_TOKEN", "")

# Email sender used only for SMTP RCPT-TO verification
SMTP_FROM_ADDR = os.getenv("SMTP_FROM_ADDR", "verify@example.com")
SMTP_TIMEOUT = int(os.getenv("SMTP_TIMEOUT", "8"))

SCRAPE_LIMIT_PER_TAG = 50
QUALIFY_BATCH_LIMIT = 100
GUESSED_EMAILS_TO_DRAFT = os.getenv("GUESSED_EMAILS_TO_DRAFT", "false").lower() in ("1", "true", "yes", "on")

# --- Tiered Cache (V2) ---
# Upstash: rediss://USERNAME:PASSWORD@HOST:PORT  |  Local: redis://localhost:6379
REDIS_URL = os.getenv("REDIS_URL", "")

# --- Cloudflare R2 (V2 zero-leak sync) ---
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET = os.getenv("R2_BUCKET", "lead-engine")
R2_REGION = os.getenv("R2_REGION", "auto")

# --- Browser Automation (V2) ---
AUTO_APPLY = os.getenv("AUTO_APPLY", "false").lower() == "true"
WELLFOUND_SESSION_FILE = os.getenv(
    "WELLFOUND_SESSION_FILE", "wellfound_session.json"
)
WELLFOUND_PROFILE_URL = os.getenv(
    "WELLFOUND_PROFILE_URL", "https://wellfound.com/account/profile"
)
BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "true").lower() != "false"

# --- Copilot links (V2) ---
LINKEDIN_CONNECT_LIMIT_PER_DAY = int(os.getenv("LINKEDIN_CONNECT_LIMIT_PER_DAY", "15"))
X_DM_LIMIT_PER_DAY = int(os.getenv("X_DM_LIMIT_PER_DAY", "15"))
