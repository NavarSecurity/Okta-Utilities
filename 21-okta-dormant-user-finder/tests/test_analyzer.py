import json
from datetime import datetime, timezone
from pathlib import Path

from okta_dormant_user_finder.analyzer import DormantUserFinder, analyze_user, read_users_file
from okta_dormant_user_finder.config import AppConfig, SourceConfig


def config_file_mode(tmp_path):
    return AppConfig(org_url="https://example.okta.com", source=SourceConfig(mode="file", users_file=str(tmp_path / "users.csv")))


def test_analyze_never_logged_in():
    config = AppConfig(org_url="https://example.okta.com")
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)
    result = analyze_user({
        "id": "00u1",
        "status": "ACTIVE",
        "created": "2026-01-01T00:00:00.000Z",
        "profile": {"login": "never@example.com", "email": "never@example.com"},
    }, config, now=now)
    assert result["isDormantCandidate"] is True
    assert "NEVER_LOGGED_IN" in result["reasons"]


def test_analyze_stale_login():
    config = AppConfig(org_url="https://example.okta.com")
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)
    result = analyze_user({
        "id": "00u1",
        "status": "ACTIVE",
        "created": "2025-01-01T00:00:00.000Z",
        "lastLogin": "2025-01-01T00:00:00.000Z",
        "profile": {"login": "stale@example.com", "email": "stale@example.com"},
    }, config, now=now)
    assert "STALE_LOGIN" in result["reasons"]


def test_file_mode_run(tmp_path):
    users_file = tmp_path / "users.csv"
    users_file.write_text("id,status,created,lastLogin,login,email\n00u1,ACTIVE,2026-01-01T00:00:00.000Z,,never@example.com,never@example.com\n", encoding="utf-8")
    config = AppConfig(org_url="https://example.okta.com", source=SourceConfig(mode="file", users_file=str(users_file)))
    result = DormantUserFinder(config).run()
    assert result["counts"]["usersAnalyzed"] == 1
    assert result["counts"]["dormantCandidates"] == 1


def test_read_json_users_array(tmp_path):
    path = tmp_path / "users.json"
    path.write_text(json.dumps([{"id": "1"}]), encoding="utf-8")
    assert read_users_file(path)[0]["id"] == "1"


def test_dormant_user_has_utility22_lifecycle_columns():
    config = AppConfig(org_url="https://example.okta.com")
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)
    result = analyze_user({
        "id": "00u1",
        "status": "ACTIVE",
        "created": "2026-01-01T00:00:00.000Z",
        "profile": {"login": "never@example.com", "email": "never@example.com"},
    }, config, now=now)
    assert result["action"] == "deprovision"
    assert result["approved"] == ""
    assert result["reason"].startswith("Dormant user review candidate:")
    assert "NEVER_LOGGED_IN" in result["reason"]
