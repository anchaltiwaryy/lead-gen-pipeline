"""Tests for structured logging."""
import logging
from logger import log

def test_logger_instance():
    assert isinstance(log, logging.Logger)
    assert log.name == "pipeline"
