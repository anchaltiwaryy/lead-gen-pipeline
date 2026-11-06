# Deployment & Operations Guide

### Running Locally
```bash
# 1. Start FastAPI backend (also serves the simple dashboard at http://localhost:8000)
python api.py

# 2. Optional: start the full Next.js control center
cd dashboard && npm run dev
```

To try the dashboard without real data: `python seed_demo.py` then `python api.py --demo`.

### Production Checklist
- Configure `.env` with `PRIMARY_AI_PROVIDER=gemini` and `GEMINI_MODEL=gemini-3.6-flash`.
- Authorize Gmail via `python auth_gmail.py`.
- Sync state to Cloudflare R2 via `python sync_r2.py push`.
