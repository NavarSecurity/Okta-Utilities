from okta_mfa_reset.planner import build_plan
from okta_mfa_reset.config import DEFAULT_COLUMNS, DEFAULT_SETTINGS, normalize_org_url, ConfigError
import pytest


def test_plan_approved_reset_all():
    rows = [{
        "userId": "00u1",
        "login": "user@example.com",
        "email": "user@example.com",
        "action": "reset_all_factors",
        "approved": "true",
        "reason": "ticket approved",
    }]
    plan = build_plan(rows, DEFAULT_SETTINGS, DEFAULT_COLUMNS)
    assert plan["summary"]["plannedActions"] == 1
    assert plan["plannedActions"][0]["action"] == "reset_all_factors"


def test_skip_unapproved():
    rows = [{
        "userId": "00u1",
        "login": "user@example.com",
        "email": "user@example.com",
        "action": "reset_all_factors",
        "approved": "",
        "reason": "ticket approved",
    }]
    plan = build_plan(rows, DEFAULT_SETTINGS, DEFAULT_COLUMNS)
    assert plan["summary"]["plannedActions"] == 0
    assert "not approved" in plan["skippedRows"][0]["skipReason"]


def test_delete_factor_requires_factor_info():
    rows = [{
        "userId": "00u1",
        "login": "user@example.com",
        "email": "user@example.com",
        "action": "delete_factor",
        "approved": "true",
        "reason": "ticket approved",
    }]
    plan = build_plan(rows, DEFAULT_SETTINGS, DEFAULT_COLUMNS)
    assert plan["summary"]["plannedActions"] == 0
    assert "requires factorId or factorType" in plan["skippedRows"][0]["skipReason"]


def test_protected_login_skipped():
    rows = [{
        "userId": "00u1",
        "login": "admin@example.com",
        "email": "admin@example.com",
        "action": "reset_all_factors",
        "approved": "true",
        "reason": "ticket approved",
    }]
    plan = build_plan(rows, DEFAULT_SETTINGS, DEFAULT_COLUMNS)
    assert plan["summary"]["plannedActions"] == 0
    assert "protected" in plan["skippedRows"][0]["skipReason"]


def test_admin_url_rejected():
    with pytest.raises(ConfigError):
        normalize_org_url("https://example-admin.okta.com")
