import csv
from pathlib import Path

import pytest

from okta_group_membership_loader.config import LoaderConfig
from okta_group_membership_loader.runner import build_plan, RunnerError
from okta_group_membership_loader.models import MembershipRequest, SkippedRecord
from okta_group_membership_loader.runner import validate_request


def make_csv(tmp_path, rows):
    p = tmp_path / "members.csv"
    fields = ["groupId", "groupName", "userId", "login", "email", "action", "approved", "reason"]
    with p.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return p


def test_builds_add_plan_without_api_when_verification_disabled(tmp_path):
    p = make_csv(tmp_path, [{"groupId": "g1", "userId": "u1", "action": "add", "approved": "true", "reason": "approved"}])
    cfg = LoaderConfig("https://example.okta.com", str(p), settings={"verifyExistingStateInDryRun": False})
    planned, skipped, failed, summary = build_plan(cfg, client=None)
    assert len(planned) == 1
    assert planned[0].rollback_method == "DELETE"
    assert not skipped
    assert not failed


def test_skips_unapproved_row(tmp_path):
    p = make_csv(tmp_path, [{"groupId": "g1", "userId": "u1", "action": "add", "approved": "", "reason": "approved"}])
    cfg = LoaderConfig("https://example.okta.com", str(p), settings={"verifyExistingStateInDryRun": False})
    planned, skipped, failed, summary = build_plan(cfg, client=None)
    assert not planned
    assert skipped[0].reason == "Row was not approved for group membership action."


def test_remove_blocked_by_default(tmp_path):
    p = make_csv(tmp_path, [{"groupId": "g1", "userId": "u1", "action": "remove", "approved": "true", "reason": "approved"}])
    cfg = LoaderConfig("https://example.okta.com", str(p), settings={"verifyExistingStateInDryRun": False})
    planned, skipped, failed, summary = build_plan(cfg, client=None)
    assert not planned
    assert "allowRemove=false" in skipped[0].reason


def test_remove_allowed_has_put_rollback(tmp_path):
    p = make_csv(tmp_path, [{"groupId": "g1", "userId": "u1", "action": "remove", "approved": "true", "reason": "approved"}])
    cfg = LoaderConfig("https://example.okta.com", str(p), safety={"allowRemove": True}, settings={"verifyExistingStateInDryRun": False})
    planned, skipped, failed, summary = build_plan(cfg, client=None)
    assert len(planned) == 1
    assert planned[0].rollback_method == "PUT"


def test_replace_blocked_by_default():
    row = MembershipRequest(2, "replace", group_id="g1", user_id="u1", approved="true", reason="approved")
    cfg = LoaderConfig("https://example.okta.com", "input/a.csv")
    skipped = []
    assert not validate_request(row, cfg, skipped)
    assert "allowReplace=false" in skipped[0].reason


def test_max_changes_limit(tmp_path):
    p = make_csv(tmp_path, [
        {"groupId": "g1", "userId": "u1", "action": "add", "approved": "true", "reason": "approved"},
        {"groupId": "g1", "userId": "u2", "action": "add", "approved": "true", "reason": "approved"},
    ])
    cfg = LoaderConfig("https://example.okta.com", str(p), safety={"maxChangesPerRun": 1}, settings={"verifyExistingStateInDryRun": False})
    with pytest.raises(RunnerError):
        build_plan(cfg, client=None)
