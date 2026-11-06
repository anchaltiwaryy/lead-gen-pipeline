"""Tests for dashboard data schemas."""
import pytest
from api import LeadEdit, StatusUpdate

def test_status_update_schema():
    up = StatusUpdate(status="qualified")
    assert up.status == "qualified"

def test_lead_edit_schema():
    edit = LeadEdit(draft_email_body="Updated pitch", custom_notes="Call scheduled")
    assert edit.draft_email_body == "Updated pitch"
