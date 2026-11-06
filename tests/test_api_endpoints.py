"""Tests for FastAPI application endpoints."""
import pytest
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def test_api_stats():
    res = client.get("/api/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "by_status" in data

def test_api_leads_list():
    res = client.get("/api/leads?limit=5")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
