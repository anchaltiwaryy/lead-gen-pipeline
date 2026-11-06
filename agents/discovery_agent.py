"""Agent 1 - Discovery Agent.

Translates the active target profile into structured, source-specific search
strategies and crawls unauthenticated feeds (DuckDuckGo news/web, Google Dorks,
VC portfolios, startup directories) for fresh, small, funded companies.

Reuses the battle-tested query_gen + discover_startups routines from the
root pipeline modules; the agent simply wraps them with a typed interface.
"""
from __future__ import annotations

import json
from typing import Optional

from config import DISCOVERY_QUERIES_PER_RUN
from db import get_conn, count_by_status
from logger import log

import query_gen
import discover_startups


class DiscoveryAgent:
    """Multi-channel query generator & Google Dorks crawler."""

    name = "discovery"

    def __init__(self, limit: int = DISCOVERY_QUERIES_PER_RUN):
        self.limit = limit

    def generate_queries(self) -> dict:
        """Generate funding/hiring/source queries from the active profile."""
        queries = query_gen.generate_queries()
        total = sum(len(v) for v in queries.values() if isinstance(v, list))
        log.info(f"[discovery] generated {total} search queries")
        return queries

    def run(self, queries: Optional[dict] = None) -> int:
        """Execute the search crawl and insert fresh leads as status='new'."""
        conn = get_conn()
        before = count_by_status(conn).get("new", 0)
        conn.close()
        log.info("[discovery] starting multi-channel discovery crawl")
        q = queries or self.generate_queries()
        inserted = discover_startups.discover_startups(q, limit=self.limit)
        conn = get_conn()
        after = count_by_status(conn).get("new", 0)
        conn.close()
        log.info(f"[discovery] inserted {inserted} leads (new count {before} -> {after})")
        return inserted

    def __repr__(self) -> str:
        return f"<DiscoveryAgent limit={self.limit}>"