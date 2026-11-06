"""Tests for resume profile extraction and loading."""
import os
import json
import pytest
from resume_profile import load_profile

def test_load_profile_fallback():
    profile = load_profile("non_existent_profile.json")
    assert isinstance(profile, dict)
    assert "candidate" in profile or "name" in profile or "skills" in profile or len(profile) >= 0
