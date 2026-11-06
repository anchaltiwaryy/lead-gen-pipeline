"""Tests for search query generation."""
import pytest
from query_gen import PROMPT

def test_query_prompt_template():
    assert "Candidate profile" in PROMPT
    assert "target_roles" in PROMPT
