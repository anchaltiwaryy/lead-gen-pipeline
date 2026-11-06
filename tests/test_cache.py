"""Tests for tiered cache-aside engine."""
import sqlite3
import pytest
from cache import Cache

def test_cache_sqlite_fallback():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE kv_cache (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            created_at INTEGER NOT NULL
        )
    """)
    cache = Cache(conn_factory=lambda: conn)
    cache.set("test_key", {"foo": "bar"}, ttl=3600)
    res = cache.get("test_key")
    assert res == {"foo": "bar"}
