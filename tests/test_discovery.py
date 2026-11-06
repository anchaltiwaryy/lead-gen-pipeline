"""Unit tests for discovery sources and board slug extraction."""
import pytest
from discovery_sources import extract_from_board_url, build_source_queries


def test_greenhouse_slug_extraction():
    url = "https://boards.greenhouse.io/anthropic/jobs/123456"
    slug, host = extract_from_board_url(url)
    assert slug == "anthropic"
    assert host == "boards.greenhouse.io"


def test_lever_slug_extraction():
    url = "https://jobs.lever.co/notion/abc-123-xyz"
    slug, host = extract_from_board_url(url)
    assert slug == "notion"
    assert host == "jobs.lever.co"


def test_ashby_slug_extraction():
    url = "https://jobs.ashbyhq.com/perplexity"
    slug, host = extract_from_board_url(url)
    assert slug == "perplexity"
    assert host == "jobs.ashbyhq.com"


def test_non_board_url():
    url = "https://example.com/careers"
    res = extract_from_board_url(url)
    assert res is None


def test_build_source_queries():
    roles = ["AI Engineer", "DevRel"]
    regions = ["US", "Europe"]
    queries = build_source_queries(roles, regions)
    assert len(queries) > 0
    assert any("greenhouse" in q for q in queries)
