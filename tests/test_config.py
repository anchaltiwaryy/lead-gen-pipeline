"""Tests for configuration settings and active profiles."""
import os
import pytest
from config import PROFILES, ACTIVE_PROFILE, PRIMARY_AI_PROVIDER, GEMINI_MODEL

def test_profiles_structure():
    assert "engineering" in PROFILES
    assert "gtm_devrel" in PROFILES
    assert len(PROFILES["engineering"]["target_roles"]) > 0
    assert len(PROFILES["gtm_devrel"]["target_roles"]) > 0

def test_primary_ai_config():
    assert PRIMARY_AI_PROVIDER == "gemini"
    assert "gemini" in GEMINI_MODEL.lower()
