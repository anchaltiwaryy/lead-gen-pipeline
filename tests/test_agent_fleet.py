"""Tests for agent fleet modules."""
import pytest
from agents import (
    DiscoveryAgent,
    WebIntelAgent,
    QualificationAgent,
    EnrichmentAgent,
    PitchAgent,
    BrowserAgent,
)

def test_agent_classes():
    assert DiscoveryAgent.name == "discovery"
    assert WebIntelAgent.name == "web_intel"
    assert QualificationAgent.name == "qualification"
    assert EnrichmentAgent.name == "enrichment"
    assert PitchAgent.name == "pitch"
    assert BrowserAgent.name == "browser"
