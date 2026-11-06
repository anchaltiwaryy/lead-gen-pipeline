"""Tests for PitchBundle model."""
import pytest
from agents.pitch_agent import PitchBundle

def test_pitch_bundle_validation():
    bundle = PitchBundle(
        email_body="Hi Founder, noticed your recent seed round...",
        linkedin_note="Excited by Acme AI's product direction. Would love to connect!",
        x_dm="Hey! Saw the launch on X."
    )
    assert len(bundle.linkedin_note) <= 300
    assert "Acme AI" in bundle.linkedin_note
