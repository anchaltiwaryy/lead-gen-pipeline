"""Tests for discovery sources and job board dorks."""
import pytest
from discovery_sources import extract_from_board_url, build_source_queries

def test_extract_greenhouse():
    res = extract_from_board_url("https://boards.greenhouse.io/acmeai/jobs/12345")
    assert res is not None
    assert res[0].lower() == "acmeai"

def test_extract_lever():
    res = extract_from_board_url("https://jobs.lever.co/datasync/67890")
    assert res is not None
    assert res[0].lower() == "datasync"
