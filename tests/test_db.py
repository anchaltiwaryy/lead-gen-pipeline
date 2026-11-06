"""Unit tests for SQLite database operations, WAL mode, and suppression list."""
import sqlite3
import pytest
from db import get_conn, insert_lead, get_leads_by_status, update_lead, add_to_suppression, is_suppressed


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_leads.db"
    conn = get_conn(str(db_file))
    yield conn
    conn.close()


def test_db_wal_mode(test_db):
    cur = test_db.execute("PRAGMA journal_mode;")
    mode = cur.fetchone()[0]
    assert mode.lower() == "wal"


def test_insert_and_get_lead(test_db):
    insert_lead(
        test_db,
        company="Anthropic",
        job_url="https://anthropic.com/careers/1",
        source="test_query",
        company_domain="anthropic.com",
        role_title="AI Engineer",
    )
    leads = get_leads_by_status(test_db, "new")
    assert len(leads) == 1
    assert leads[0]["company"] == "Anthropic"
    assert leads[0]["company_domain"] == "anthropic.com"


def test_suppression_list(test_db):
    add_to_suppression(test_db, "blockedcompany.com", "opt_out")
    assert is_suppressed(test_db, "blockedcompany.com") is True
    assert is_suppressed(test_db, "ceo@blockedcompany.com") is True
    assert is_suppressed(test_db, "allowed.com") is False

    # Insert on suppressed domain should be blocked
    insert_lead(
        test_db,
        company="Blocked Co",
        job_url="https://blockedcompany.com/job",
        source="test",
        company_domain="blockedcompany.com",
    )
    leads = get_leads_by_status(test_db, "new")
    assert not any(l["company"] == "Blocked Co" for l in leads)
