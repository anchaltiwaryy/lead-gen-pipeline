"""Integration test suite for end-to-end pipeline."""
import pytest
from db import get_conn, count_by_status

def test_db_connection():
    conn = get_conn()
    counts = count_by_status(conn)
    assert isinstance(counts, dict)
    conn.close()
