import csv
import json
from pathlib import Path

from okta_user_deactivator.config import load_config
from okta_user_deactivator.models import ActionResult, PlanItem
from okta_user_deactivator.reports import rollback_entry, write_results
from okta_user_deactivator.runner import apply_one, run


class FakeClient:
    def __init__(self, status="ACTIVE"):
        self.status = status
        self.deleted = False
        self.deactivated = False

    def get_user(self, identifier):
        return {"id": "00u1", "status": self.status, "profile": {"login": "u@example.com"}}

    def suspend_user(self, user_id):
        return {}

    def deactivate_user(self, user_id, send_email=False):
        self.deactivated = True
        return {}

    def delete_user(self, user_id, send_email=False):
        self.deleted = True
        return {}


def test_rollback_entry_for_suspend():
    result = ActionResult(2, "u@example.com", "00u1", "u@example.com", "suspend", "ACTIVE", "SUSPENDED", True, False, "ok", rollback_action="unsuspend", rollback_endpoint="POST /x")
    entry = rollback_entry(result)
    assert entry["rollbackAction"] == "unsuspend"
    assert entry["userId"] == "00u1"


def test_no_rollback_entry_for_delete():
    result = ActionResult(2, "u@example.com", "00u1", "u@example.com", "delete", "DEPROVISIONED", "DELETED", True, False, "ok")
    assert rollback_entry(result) is None


def test_write_results_creates_report(tmp_path):
    plan = [PlanItem(2, "u@example.com", "", "u@example.com", "u@example.com", "deprovision", True, "test", True, "PLANNED", "ok")]
    result = ActionResult(2, "u@example.com", "00u1", "u@example.com", "deprovision", "ACTIVE", "DEPROVISIONED", True, False, "ok", rollback_action="activate", rollback_endpoint="POST /x")
    write_results(tmp_path, "apply", plan, [result], [])
    assert (tmp_path / "execution_report.md").exists()
    assert (tmp_path / "rollback_plan.json").exists()
    assert (tmp_path / "user_lifecycle_result.json").exists()
    assert (tmp_path / "user_deactivation_result.json").exists()


def test_delete_requires_deprovisioned_status_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    csv_path = tmp_path / "users.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "login", "email", "action", "approved", "reason"])
        writer.writeheader()
        writer.writerow({"login": "u@example.com", "action": "delete", "approved": "true", "reason": "cleanup"})
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "targetOrgUrl": "https://example.okta.com",
        "apiToken": "token",
        "inputFile": str(csv_path),
        "settings": {"allowDeleteDeprovisionedUsers": True}
    }), encoding="utf-8")
    config = load_config(config_path)
    item = PlanItem(2, "u@example.com", "", "u@example.com", "u@example.com", "delete", True, "cleanup", True, "PLANNED", "ok")
    client = FakeClient(status="ACTIVE")
    result = apply_one(item, config, client)
    assert result.skipped is True
    assert client.deleted is False
    assert "not DEPROVISIONED" in result.message


def test_delete_deprovisioned_user_when_enabled(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    csv_path = tmp_path / "users.csv"
    csv_path.write_text("id,login,email,action,approved,reason\n,u@example.com,u@example.com,delete,true,cleanup\n", encoding="utf-8")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "targetOrgUrl": "https://example.okta.com",
        "apiToken": "token",
        "inputFile": str(csv_path),
        "settings": {"allowDeleteDeprovisionedUsers": True}
    }), encoding="utf-8")
    config = load_config(config_path)
    item = PlanItem(2, "u@example.com", "", "u@example.com", "u@example.com", "delete", True, "cleanup", True, "PLANNED", "ok")
    client = FakeClient(status="DEPROVISIONED")
    result = apply_one(item, config, client)
    assert result.success is True
    assert result.result_status == "DELETED"
    assert client.deleted is True


def test_dry_run_creates_output_without_api(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    csv_path = tmp_path / "users.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "login", "email", "action", "approved", "reason"])
        writer.writeheader()
        writer.writerow({"login": "user@example.com", "action": "suspend", "approved": "true", "reason": "test"})
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "targetOrgUrl": "https://example.okta.com",
        "apiToken": "token",
        "inputFile": str(csv_path),
        "outputDir": str(tmp_path / "output"),
        "settings": {"verifyUsersOnDryRun": False}
    }), encoding="utf-8")
    output = run(load_config(config_path), mode="dry-run")
    assert (output / "user_lifecycle_plan.csv").exists()
    assert (output / "user_deactivation_plan.csv").exists()
    assert (output / "execution_report.md").exists()
