# Deployment & Operations Guide

### Running Locally
```bash
# 1. Start FastAPI backend
python api.py

# 2. Start Next.js dashboard UI
cd dashboard && npm run dev
```

### Production Checklist
- Configure `.env` with `PRIMARY_AI_PROVIDER=gemini` and `GEMINI_MODEL=gemini-3.6-flash`.
- Authorize Gmail via `python auth_gmail.py`.
- Sync state to Cloudflare R2 via `python sync_r2.py push`.
