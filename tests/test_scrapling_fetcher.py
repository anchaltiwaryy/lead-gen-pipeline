"""Tests for URL extraction and domain resolution."""
import pytest
from tld import get_fld

def test_get_fld_domain():
    assert get_fld("https://sub.domain.co.uk/path", fix_protocol=True) == "domain.co.uk"
    assert get_fld("https://company.ai/careers", fix_protocol=True) == "company.ai"
