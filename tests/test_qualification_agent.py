"""Tests for qualification agent Pydantic models."""
import pytest
from agents.qualification_agent import FitScore

def test_fit_score_model():
    score = FitScore(fit_score=85, reason="High fit with candidate AI agent experience.")
    assert score.fit_score == 85
    assert score.passes is True

def test_fit_score_rejection():
    score = FitScore(fit_score=30, reason="Location requires non-remote relocation.")
    assert score.fit_score == 30
    assert score.passes is False
