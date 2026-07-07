import csv
import json
from pathlib import Path

import pytest

from okta_user_deactivator.config import load_config
from okta_user_deactivator.planner import build_plan, read_user_requests


def make_config(tmp_path: Path, csv_path: Path, **settings):
    data = {
        "targetOrgUrl": "https://example.okta.com",
        "apiToken": "token",
        "inputFile": str(csv_path),
        "settings": {"defaultAction": "suspend", "requireApproved": True, "requireReason": True, **settings},
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return load_config(path)


def write_csv(path: Path, rows):
    fieldnames = ["id", "login", "email", "action", "approved", "reason"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_plan_accepts_approved_suspend_user(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    csv_path = tmp_path / "users.csv"
    write_csv(csv_path, [{"login": "user@example.com", "action": "suspend", "approved": "true", "reason": "test"}])
    config = make_config(tmp_path, csv_path)
    plan = build_plan(read_user_requests(csv_path, config), config)
    assert plan[0].planned is True
    assert plan[0].action == "suspend"


def test_plan_accepts_deprovision_and_deactivate_alias(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    csv_path = tmp_path / "users.csv"
    write_csv(csv_path, [
        {"login": "user1@example.com", "action": "deprovision", "approved": "true", "reason": "test"},
        {"login": "user2@example.com", "action": "deactivate", "approved": "true", "reason": "test"},
    ])
    config = make_config(tmp_path, csv_path)
    plan = build_plan(read_user_requests(csv_path, config), config)
    assert [p.action for p in plan] == ["deprovision", "deprovision"]
    assert all(p.planned for p in plan)


def test_delete_is_blocked_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    csv_path = tmp_path / "users.csv"
    write_csv(csv_path, [{"login": "user@example.com", "action": "delete", "approved": "true", "reason": "test"}])
    config = make_config(tmp_path, csv_path)
    plan = build_plan(read_user_requests(csv_path, config), config)
    assert plan[0].planned is False
    assert "Delete action is disabled" in plan[0].message


def test_delete_is_allowed_when_enabled(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    csv_path = tmp_path / "users.csv"
    write_csv(csv_path, [{"login": "user@example.com", "action": "delete", "approved": "true", "reason": "test"}])
    config = make_config(tmp_path, csv_path, allowDeleteDeprovisionedUsers=True)
    plan = build_plan(read_user_requests(csv_path, config), config)
    assert plan[0].planned is True
    assert plan[0].action == "delete"


def test_plan_skips_unapproved_user(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    csv_path = tmp_path / "users.csv"
    write_csv(csv_path, [{"login": "user@example.com", "action": "suspend", "approved": "false", "reason": "test"}])
    config = make_config(tmp_path, csv_path)
    plan = build_plan(read_user_requests(csv_path, config), config)
    assert plan[0].planned is False
    assert "not approved" in plan[0].message


def test_plan_skips_missing_reason(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    csv_path = tmp_path / "users.csv"
    write_csv(csv_path, [{"login": "user@example.com", "action": "suspend", "approved": "true", "reason": ""}])
    config = make_config(tmp_path, csv_path)
    plan = build_plan(read_user_requests(csv_path, config), config)
    assert plan[0].planned is False
    assert "Reason" in plan[0].message


def test_plan_skips_admin_pattern(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    csv_path = tmp_path / "users.csv"
    write_csv(csv_path, [{"login": "admin@example.com", "action": "suspend", "approved": "true", "reason": "test"}])
    config = make_config(tmp_path, csv_path)
    plan = build_plan(read_user_requests(csv_path, config), config)
    assert plan[0].planned is False
    assert "blocked" in plan[0].message.lower()


def test_plan_blocks_too_many_users(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    csv_path = tmp_path / "users.csv"
    write_csv(csv_path, [
        {"login": "user1@example.com", "action": "suspend", "approved": "true", "reason": "test"},
        {"login": "user2@example.com", "action": "suspend", "approved": "true", "reason": "test"},
    ])
    config = make_config(tmp_path, csv_path, maxUsersPerRun=1)
    with pytest.raises(ValueError):
        build_plan(read_user_requests(csv_path, config), config)
