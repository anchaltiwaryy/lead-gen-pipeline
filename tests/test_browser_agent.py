"""Tests for browser automation jitter and configuration."""
import pytest
from agents.browser_agent import BrowserAgent
from config import WELLFOUND_PROFILE_URL

def test_browser_agent_config():
    agent = BrowserAgent()
    assert agent.profile_url == WELLFOUND_PROFILE_URL
