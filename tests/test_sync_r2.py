"""Tests for Cloudflare R2 S3 sync client."""
import pytest
from sync_r2 import _client, R2_BUCKET

def test_r2_bucket_config():
    assert isinstance(R2_BUCKET, str)
