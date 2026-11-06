"""Tests for SMTP verification and MX record queries."""
import pytest
from enrich_email import _verify_smtp_rcpt_to

def test_smtp_mock_empty():
    assert _verify_smtp_rcpt_to("invalid-email-address") is False
