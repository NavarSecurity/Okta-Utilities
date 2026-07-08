from __future__ import annotations

import json
from pathlib import Path

import pytest

from okta_group_cleanup_analyzer import analyzer as analyzer_module
from okta_group_cleanup_analyzer.analyzer import analyze, normalize_name
from okta_group_cleanup_analyzer.config import ConfigError, load_config, validate_config, validate_org_url
from okta_group_cleanup_analyzer.models import GroupRecord


def base_config(tmp_path: Path) -> dict:
    return {
        "mode": "api",
        "orgUrl": "https://example.okta.com",
        "apiToken": "test-token",
        "analysis": {
            "findEmptyGroups": True,
            "findUnusedGroups": True,
            "findDuplicateNames": True,
            "findStaleGroups": False,
            "findOwnerlessGroups": True,
            "ownerFields": ["owner"],
            "protectedGroupNamePatterns": ["admin"],
        },
        "settings": {
            "includeOktaBuiltInGroups": False,
            "fetchMemberCountsInApiMode": True,
            "fetchAppAssignmentCountsInApiMode": True,
            "fetchRuleTargetCountsInApiMode": True,
            "strictMode": False,
        },
        "outputDir": str(tmp_path / "output"),
    }


def mock_api_groups(config: dict, owner_fields: list[str]):
    groups = [
        GroupRecord(id="00g1", name="Group A", owner="owner@example.com", member_count=2, app_assignment_count=1, rule_target_count=1),
        GroupRecord(id="00g2", name="Empty Group", owner="", member_count=0, app_assignment_count=0, rule_target_count=0),
        GroupRecord(id="00g3", name="Duplicate", owner="", member_count=0, app_assignment_count=0, rule_target_count=0),
        GroupRecord(id="00g4", name=" duplicate ", owner="", member_count=0, app_assignment_count=0, rule_target_count=0),
        GroupRecord(id="00g5", name="Super Admins", owner="admin@example.com", member_count=0, app_assignment_count=0, rule_target_count=0),
    ]
    evidence = {
        "groupsFetched": True,
        "memberCountsFetched": True,
        "appAssignmentCountsFetched": True,
        "ruleTargetCountsFetched": True,
    }
    return groups, 12, [], evidence


def test_normalize_name_collapses_spacing_and_case() -> None:
    assert normalize_name("  Duplicate   GROUP ") == "duplicate group"


def test_analyze_finds_cleanup_categories_from_api(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(analyzer_module, "load_groups_from_api", mock_api_groups)
    result = analyze(base_config(tmp_path), dry_run=False)
    assert result["analysisMode"] == "api"
    assert result["totalGroupsAnalyzed"] == 5
    assert result["counts"]["emptyGroups"] == 4
    assert result["counts"]["unusedGroups"] == 4
    assert result["counts"]["duplicateGroups"] == 2
    assert result["counts"]["ownerlessGroups"] == 3
    assert result["counts"]["protectedGroups"] == 1


def test_preserves_counts_from_api(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(analyzer_module, "load_groups_from_api", mock_api_groups)
    result = analyze(base_config(tmp_path), dry_run=False)
    rows = {row["id"]: row for row in result["groups"]}
    assert rows["00g1"]["memberCount"] == 2
    assert rows["00g1"]["appAssignmentCount"] == 1
    assert rows["00g1"]["ruleTargetCount"] == 1
    assert "UNUSED_GROUP" not in rows["00g1"]["reasonCodes"]


def test_protected_group_is_review_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(analyzer_module, "load_groups_from_api", mock_api_groups)
    result = analyze(base_config(tmp_path), dry_run=False)
    protected = [g for g in result["candidates"] if g["name"] == "Super Admins"][0]
    assert protected["isProtected"] == "true"
    assert protected["recommendation"] == "protected_review_only"


def test_skips_empty_and_unused_when_evidence_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def partial_evidence(config: dict, owner_fields: list[str]):
        groups = [GroupRecord(id="00g1", name="Unknown Count Group", owner="")]
        evidence = {
            "groupsFetched": True,
            "memberCountsFetched": False,
            "appAssignmentCountsFetched": False,
            "ruleTargetCountsFetched": False,
        }
        return groups, 1, [], evidence

    monkeypatch.setattr(analyzer_module, "load_groups_from_api", partial_evidence)
    result = analyze(base_config(tmp_path), dry_run=False)
    assert result["counts"]["emptyGroups"] == 0
    assert result["counts"]["unusedGroups"] == 0
    assert result["counts"]["ownerlessGroups"] == 1
    assert result["evidenceWarnings"]


def test_dry_run_returns_api_plan(tmp_path: Path) -> None:
    result = analyze(base_config(tmp_path), dry_run=True)
    assert result["mode"] == "dry-run"
    assert result["analysisMode"] == "api"
    assert "Read current Okta groups from the Okta API" in result["plannedActions"]


def test_admin_url_rejected() -> None:
    with pytest.raises(ConfigError):
        validate_org_url("https://example-admin.okta.com")


def test_file_mode_is_rejected() -> None:
    with pytest.raises(ConfigError):
        validate_config({"mode": "file", "orgUrl": "https://example.okta.com", "apiToken": "test"})


def test_load_config_defaults_to_api_and_requires_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    monkeypatch.delenv("OKTA_ORG_URL", raising=False)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"orgUrl": "https://example.okta.com"}), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(config_path)


def test_load_config_accepts_api_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    monkeypatch.delenv("OKTA_ORG_URL", raising=False)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "mode": "api",
        "orgUrl": "https://example.okta.com",
        "apiToken": "test-token",
    }), encoding="utf-8")
    config = load_config(config_path)
    assert config["mode"] == "api"
    assert config["apiToken"] == "test-token"
