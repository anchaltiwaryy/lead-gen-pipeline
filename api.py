"""FastAPI Orchestration Layer - lead CRUD, filtering, stage triggers, SSE.

Run with:
    python api.py            # uvicorn on 0.0.0.0:8000
    python api.py --demo     # same, but on demo.db (see seed_demo.py)

Endpoints:
    GET  /                             simple dashboard (web/index.html)
    GET  /api/leads                    filterable lead board
    GET  /api/leads/{id}               full lead detail
    POST /api/leads/{id}/status        transition status
    POST /api/leads/{id}/edit          edit draft body / linkedin note / notes
    GET  /api/stats                    funnel + score + source analytics
    POST /api/pipeline/run             trigger stage execution (async)
    GET  /api/pipeline/logs/stream     SSE live pipeline logs
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

# `--demo` must switch the DB before config.py reads DB_PATH on import.
if __name__ == "__main__" and "--demo" in sys.argv:
    os.environ["DB_PATH"] = "demo.db"

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from db import get_conn, get_lead, query_leads, funnel_stats, update_lead
from loghub import hub, StdoutTee
from logger import log

VALID_STATUSES = {
    "new", "qualified", "enriched", "drafted", "draft_created",
    "sent", "applied", "replied", "rejected", "skipped", "needs_review",
}

app = FastAPI(title="Lead Intelligence Engine API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Schemas --------------------------------------------------------------

class StatusUpdate(BaseModel):
    status: str = Field(min_length=1)


class LeadEdit(BaseModel):
    draft_email_body: str | None = None
    linkedin_note: str | None = None
    x_dm: str | None = None
    custom_notes: str | None = None


class PipelineRun(BaseModel):
    stage: str = Field(pattern="^(scrape|qualify|enrich|draft|send|all)$")
    limit: int | None = Field(default=None, ge=1, le=500)


# --- Leads ----------------------------------------------------------------

@app.get("/api/leads")
def list_leads(
    status: str | None = Query(default=None),
    min_score: int | None = Query(default=None, ge=0, le=100),
    source: str | None = Query(default=None),
    search_query: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    conn = get_conn()
    try:
        rows = query_leads(
            conn,
            status=status,
            min_score=min_score,
            source=source,
            search_query=search_query,
            limit=limit,
            offset=offset,
        )
        return {"total": len(rows), "items": rows}
    finally:
        conn.close()


@app.get("/api/leads/{lead_id}")
def lead_detail(lead_id: int):
    conn = get_conn()
    try:
        lead = get_lead(conn, lead_id)
    finally:
        conn.close()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@app.post("/api/leads/{lead_id}/status")
def change_status(lead_id: int, body: StatusUpdate):
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status '{body.status}'")
    conn = get_conn()
    try:
        if not get_lead(conn, lead_id):
            raise HTTPException(status_code=404, detail="Lead not found")
        update_lead(conn, lead_id, status=body.status)
        return {"id": lead_id, "status": body.status}
    finally:
        conn.close()


@app.post("/api/leads/{lead_id}/edit")
def edit_lead(lead_id: int, body: LeadEdit):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=422, detail="No editable fields provided")
    conn = get_conn()
    try:
        if not get_lead(conn, lead_id):
            raise HTTPException(status_code=404, detail="Lead not found")
        update_lead(conn, lead_id, **updates)
        return {"id": lead_id, "updated": list(updates.keys())}
    finally:
        conn.close()


@app.post("/api/leads/{lead_id}/gmail-draft")
async def create_gmail_draft(lead_id: int):
    """1-Click copilot: create a Gmail draft for a single drafted lead."""
    conn = get_conn()
    try:
        lead = get_lead(conn, lead_id)
    finally:
        conn.close()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    def _build():
        import send_gmail
        to_email = lead.get("email")
        if not to_email:
            raise HTTPException(status_code=422, detail="Lead has no contact email")
        body_html = send_gmail._load_body_html(lead["company"]) or ""
        if not body_html:
            raise HTTPException(status_code=422, detail="No local draft body found")
        service = send_gmail.get_service()
        result = send_gmail.create_draft(service, to_email, send_gmail._subject(lead), body_html)
        conn = get_conn()
        try:
            update_lead(conn, lead_id, gmail_draft_id=result.get("id"), status="draft_created")
        finally:
            conn.close()
        return result

    result = await asyncio.to_thread(_build)
    return {"id": lead_id, "gmail_draft_id": result.get("id"), "status": "draft_created"}


# --- Analytics ------------------------------------------------------------

@app.get("/api/stats")
def stats():
    conn = get_conn()
    try:
        return funnel_stats(conn)
    finally:
        conn.close()


# --- Pipeline execution ---------------------------------------------------

def _run_stage_blocking(stage: str, limit: int | None) -> dict:
    import runner
    with StdoutTee():
        result = runner.run_stage(stage, limit=limit)
    return result


@app.post("/api/pipeline/run")
async def trigger_pipeline(body: PipelineRun):
    stage = body.stage

    async def _task():
        try:
            hub.emit("INFO", f"=== Pipeline stage '{stage}' starting ===")
            result = await asyncio.to_thread(_run_stage_blocking, stage, body.limit)
            hub.emit("SUCCESS", f"=== Pipeline stage '{stage}' complete: {json.dumps(result)} ===")
        except Exception as e:
            hub.emit("ERROR", f"Pipeline stage '{stage}' failed: {e}")

    asyncio.create_task(_task())
    return {"started": True, "stage": stage, "limit": body.limit}


@app.get("/api/pipeline/logs/stream")
async def stream_logs():
    async def event_gen():
        yield "event: ready\ndata: connected\n\n"
        async for line in hub.subscribe():
            payload = json.dumps(line)
            yield f"data: {payload}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


# --- Simple dashboard -----------------------------------------------------

DASHBOARD_HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "index.html")


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(DASHBOARD_HTML, media_type="text/html")


if __name__ == "__main__":
    from config import DB_PATH
    log.info(f"Starting Lead Intelligence Engine API on http://localhost:8000 (db: {DB_PATH})")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)