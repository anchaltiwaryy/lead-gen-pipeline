"""Tests for RFC 2822 email message formatting."""
import pytest
from send_gmail import build_message, encode_raw

def test_build_message_utf8():
    msg = build_message("test@example.com", "Subject Re: Engineering", "<p>Hello UTF-8 ✨</p>")
    assert msg["To"] == "test@example.com"
    assert msg["Subject"] == "Subject Re: Engineering"
    raw = encode_raw(msg)
    assert isinstance(raw, str)
