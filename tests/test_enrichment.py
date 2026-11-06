"""Unit tests for contact name splitting, candidate pattern guessing, and routing."""
import pytest
from enrich_email import split_name, guess_candidates, gate_status, _mx_is_anti_enum


def test_split_name():
    first, last = split_name("Sam Altman")
    assert first == "Sam"
    assert last == "Altman"

    first, last = split_name("Guillermo Rauch")
    assert first == "Guillermo"
    assert last == "Rauch"

    first, last = split_name("SingleName")
    assert first == "SingleName"
    assert last == ""


def test_guess_candidates():
    candidates = guess_candidates("Sam", "Altman", "openai.com")
    assert "sam.altman@openai.com" in candidates
    assert "sam@openai.com" in candidates
    assert "saltman@openai.com" in candidates


def test_anti_enum_detection():
    assert _mx_is_anti_enum("aspmx.l.google.com") is True
    assert _mx_is_anti_enum("mail.protection.outlook.com") is True
    assert _mx_is_anti_enum("mail.customhost.net") is False


def test_gate_status():
    # Verified email -> enriched
    assert gate_status("verified", True) == "enriched"
    assert gate_status("public", True) == "enriched"
    # No email -> skipped
    assert gate_status("none", False) == "skipped"
