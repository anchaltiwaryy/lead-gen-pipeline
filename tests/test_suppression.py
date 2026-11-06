"""Tests for domain and email suppression list."""
import sqlite3
import pytest
from db import get_conn, is_suppressed, add_to_suppression_list

def test_suppression_workflow():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE suppression_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT,
            email TEXT,
            reason TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    add_to_suppression_list(conn, domain="badcompany.com", email="spam@badcompany.com", reason="bounced")
    assert is_suppressed(conn, domain="badcompany.com") is True
    assert is_suppressed(conn, domain="goodcompany.com") is False
