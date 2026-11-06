"""Tests for retry utilities and exponential backoff."""
import pytest
from retry_util import with_retry

def test_with_retry_success():
    calls = 0
    @with_retry(max_retries=3, initial_delay=0.01)
    def flakily_succeed():
        nonlocal calls
        calls += 1
        if calls < 2:
            raise ValueError("transient error")
        return "success"
    
    assert flakily_succeed() == "success"
    assert calls == 2
