# FastAPI Backend Orchestration Reference

### Endpoints
- `GET /api/leads`: Query leads with filters (`status`, `min_score`, `search_query`)
- `GET /api/stats`: Conversion funnel metrics and source distribution
- `POST /api/pipeline/run`: Asynchronously trigger named worker stages
- `GET /api/pipeline/logs/stream`: SSE real-time log event stream
