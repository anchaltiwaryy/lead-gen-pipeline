"""Tests for real-time LogHub pubsub."""
import pytest
from loghub import LogHub

def test_loghub_pubsub():
    hub = LogHub(max_history=10)
    sub = hub.subscribe()
    hub.publish("INFO", "Test log message")
    msg = sub.get_nowait()
    assert msg.level == "INFO"
    assert msg.message == "Test log message"
