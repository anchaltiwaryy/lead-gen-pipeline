"""SQLite storage layer for the pipeline with WAL mode & suppression lists.

Maintains the `leads` table, `suppression_list`, and row-level helpers.
"""
import sqlite3
from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    company_domain TEXT,
    role_title TEXT,
    job_url TEXT,
    posting_text TEXT,
    funding_info TEXT,
    funding_stage TEXT,
    region TEXT,
    employee_count TEXT,
    news_url TEXT,
    source TEXT,
    fit_score INTEGER,
    fit_reason TEXT,
    contact_name TEXT,
    contact_title TEXT,
    email TEXT,
    email_confidence TEXT,
    linkedin_url TEXT,
    linkedin_company_url TEXT,
    linkedin_contact_url TEXT,
    x_url TEXT,
    gmail_draft_id TEXT,
    company_context TEXT,
    status TEXT DEFAULT 'new',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company, job_url)
);

CREATE TABLE IF NOT EXISTS suppression_list (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_or_domain TEXT UNIQUE NOT NULL,
    reason TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS kv_cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    expires_at REAL NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

_MIGRATIONS = [
    ("gmail_draft_id", "TEXT"),
    ("funding_stage", "TEXT"),
    ("region", "TEXT"),
    ("employee_count", "TEXT"),
    ("news_url", "TEXT"),
    ("linkedin_company_url", "TEXT"),
    ("linkedin_contact_url", "TEXT"),
    ("x_url", "TEXT"),
    ("company_context", "TEXT"),
    ("draft_email_body", "TEXT"),
    ("linkedin_note", "TEXT"),
    ("x_dm", "TEXT"),
    ("custom_notes", "TEXT"),
]


def get_conn(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Concurrency Hardening
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.commit()
    return conn


def _migrate(conn) -> None:
    """Add columns added after the initial schema without dropping data."""
    existing = {
        row["name"] for row in conn.execute("PRAGMA table_info(leads)").fetchall()
    }
    for col_name, col_type in _MIGRATIONS:
        if col_name not in existing:
            conn.execute(f"ALTER TABLE leads ADD COLUMN {col_name} {col_type}")


def insert_lead(conn, company, job_url, source, **fields) -> None:
    """INSERT OR IGNORE by (company, job_url); safe to re-run."""
    domain = fields.get("company_domain")
    if domain and is_suppressed(conn, domain):
        return

    values = {
        "company": company,
        "job_url": job_url,
        "source": source,
        "role_title": fields.get("role_title"),
        "company_domain": fields.get("company_domain"),
        "posting_text": fields.get("posting_text"),
        "funding_info": fields.get("funding_info"),
        "funding_stage": fields.get("funding_stage"),
        "region": fields.get("region"),
        "employee_count": fields.get("employee_count"),
        "news_url": fields.get("news_url"),
        "contact_name": fields.get("contact_name"),
        "company_context": fields.get("company_context"),
        "status": fields.get("status", "new"),
    }
    cols = ", ".join(values.keys())
    placeholders = ", ".join("?" for _ in values)
    conn.execute(
        f"INSERT OR IGNORE INTO leads ({cols}) VALUES ({placeholders})",
        tuple(values.values()),
    )
    conn.commit()


def get_leads_by_status(conn, status: str, limit: int = 100) -> list:
    cur = conn.execute(
        "SELECT * FROM leads WHERE status = ? ORDER BY created_at LIMIT ?",
        (status, limit),
    )
    return [dict(r) for r in cur.fetchall()]


def get_leads_in_statuses(conn, statuses, limit: int = 100) -> list:
    placeholders = ", ".join("?" for _ in statuses)
    cur = conn.execute(
        f"SELECT * FROM leads WHERE status IN ({placeholders}) "
        "ORDER BY created_at LIMIT ?",
        (*statuses, limit),
    )
    return [dict(r) for r in cur.fetchall()]


def get_lead(conn, lead_id: int) -> dict | None:
    cur = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def query_leads(
    conn,
    status: str | None = None,
    min_score: int | None = None,
    source: str | None = None,
    search_query: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Filtered lead search for the dashboard board. Never returns the full
    posting_text/company_context payloads (those are fetched per-lead)."""
    where, params = [], []
    if status:
        where.append("status = ?")
        params.append(status)
    if min_score is not None:
        where.append("fit_score >= ?")
        params.append(min_score)
    if source:
        where.append("source LIKE ?")
        params.append(f"%{source}%")
    if search_query:
        where.append(
            "(company LIKE ? OR role_title LIKE ? OR company_domain LIKE ?)"
        )
        like = f"%{search_query}%"
        params.extend([like, like, like])
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    cur = conn.execute(
        f"SELECT id, company, company_domain, role_title, job_url, funding_info, "
        f"funding_stage, region, employee_count, source, fit_score, fit_reason, "
        f"contact_name, contact_title, email, email_confidence, linkedin_url, "
        f"x_url, status, created_at "
        f"FROM leads {clause} ORDER BY "
        f"(fit_score IS NULL), fit_score DESC, created_at DESC LIMIT ? OFFSET ?",
        (*params, limit, offset),
    )
    return [dict(r) for r in cur.fetchall()]


def funnel_stats(conn) -> dict:
    """Funnel counts, score distribution, and source breakdown for /api/stats."""
    status_rows = conn.execute(
        "SELECT status, COUNT(*) AS n FROM leads GROUP BY status"
    ).fetchall()
    counts = {r["status"]: r["n"] for r in status_rows}

    score_rows = conn.execute(
        "SELECT CASE WHEN fit_score IS NULL THEN 'null' "
        "WHEN fit_score < 50 THEN '0-49' "
        "WHEN fit_score < 70 THEN '50-69' "
        "WHEN fit_score < 85 THEN '70-84' "
        "ELSE '85-100' END AS bucket, COUNT(*) AS n "
        "FROM leads GROUP BY bucket"
    ).fetchall()
    scores = {r["bucket"]: r["n"] for r in score_rows}

    source_rows = conn.execute(
        "SELECT source, COUNT(*) AS n FROM leads GROUP BY source "
        "ORDER BY n DESC LIMIT 20"
    ).fetchall()
    sources = {r["source"] or "unknown": r["n"] for r in source_rows}

    total = conn.execute("SELECT COUNT(*) AS n FROM leads").fetchone()["n"]
    return {
        "total": total,
        "by_status": counts,
        "score_distribution": scores,
        "by_source": sources,
    }


def update_lead(conn, lead_id: int, **kwargs) -> None:
    if not kwargs:
        return
    cols = ", ".join(f"{k} = ?" for k in kwargs)
    conn.execute(
        f"UPDATE leads SET {cols} WHERE id = ?",
        (*kwargs.values(), lead_id),
    )
    conn.commit()


def already_contacted(conn, company: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM leads WHERE company = ? AND status IN "
        "('enriched','drafted','sent','replied') LIMIT 1",
        (company,),
    )
    return cur.fetchone() is not None


def count_by_status(conn) -> dict:
    cur = conn.execute("SELECT status, COUNT(*) AS n FROM leads GROUP BY status")
    return {r["status"]: r["n"] for r in cur.fetchall()}


# --- Suppression List Management ---

def is_suppressed(conn, email_or_domain: str) -> bool:
    if not email_or_domain:
        return False
    val = email_or_domain.lower().strip()
    domain = val.split("@")[-1] if "@" in val else val
    cur = conn.execute(
        "SELECT 1 FROM suppression_list WHERE email_or_domain = ? OR email_or_domain = ? LIMIT 1",
        (val, domain),
    )
    return cur.fetchone() is not None


def add_to_suppression(conn, email_or_domain: str, reason: str = "opt_out") -> None:
    if not email_or_domain:
        return
    val = email_or_domain.lower().strip()
    conn.execute(
        "INSERT OR IGNORE INTO suppression_list (email_or_domain, reason) VALUES (?, ?)",
        (val, reason),
    )
    conn.commit()


# --- SQLite KV Cache Support ---

def db_cache_get(conn, key: str) -> str | None:
    import time
    now = time.time()
    cur = conn.execute(
        "SELECT value FROM kv_cache WHERE key = ? AND expires_at > ?",
        (key, now),
    )
    row = cur.fetchone()
    return row["value"] if row else None


def db_cache_set(conn, key: str, value: str, ttl_seconds: int = 86400) -> None:
    import time
    expires_at = time.time() + ttl_seconds
    conn.execute(
        "INSERT OR REPLACE INTO kv_cache (key, value, expires_at) VALUES (?, ?, ?)",
        (key, value, expires_at),
    )
    conn.commit()


def db_cache_delete(conn, key: str) -> None:
    conn.execute("DELETE FROM kv_cache WHERE key = ?", (key,))
    conn.commit()


def db_cache_cleanup(conn) -> int:
    import time
    now = time.time()
    cur = conn.execute("DELETE FROM kv_cache WHERE expires_at <= ?", (now,))
    conn.commit()
    return cur.rowcount