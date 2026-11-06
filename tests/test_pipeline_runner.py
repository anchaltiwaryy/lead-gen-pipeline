"""Tests for pipeline stage runner."""
import pytest
from runner import STAGES

def test_runner_stages():
    assert "scrape" in STAGES
    assert "qualify" in STAGES
    assert "enrich" in STAGES
    assert "draft" in STAGES
    assert "send" in STAGES
