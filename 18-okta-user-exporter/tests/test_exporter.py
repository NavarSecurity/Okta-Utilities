import csv
import json
from pathlib import Path

from okta_user_exporter.config import ExportConfig, Filters, Include, Settings
from okta_user_exporter.exporter import UserExporter


class FakeClient:
    def __init__(self):
        self.request_count = 4
        self.status_counts = {"200": 4}

    def list_users(self, params, max_users=None):
        users = [
            {
                "id": "00u1",
                "status": "ACTIVE",
                "created": "2026-01-01T00:00:00.000Z",
                "profile": {
                    "login": "jane@example.com",
                    "email": "jane@example.com",
                    "firstName": "Jane",
                    "lastName": "Example",
                    "department": "IT",
                    "clientSecret": "should-redact",
                },
            },
            {
                "id": "00u2",
                "status": "DEPROVISIONED",
                "profile": {"login": "old@example.com", "email": "old@example.com"},
            },
        ]
        return users[:max_users] if max_users else users

    def get_user_groups(self, user_id):
        return [{"id": "00g1", "type": "OKTA_GROUP", "profile": {"name": "Everyone", "description": "All users"}}]

    def get_user_app_links(self, user_id):
        return [{"id": "appLink1", "appInstanceId": "0oa1", "appName": "demo", "label": "Demo App", "linkUrl": "https://example.com/app"}]


def test_exporter_writes_expected_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("okta_user_exporter.exporter.OktaClient", lambda *args, **kwargs: FakeClient())
    cfg = ExportConfig(
        org_url="https://example.okta.com",
        api_token="token",
        settings=Settings(max_users=None),
        filters=Filters(statuses=["ACTIVE"], profile_fields=["login", "email", "department", "clientSecret"]),
        include=Include(groups=True, app_links=True),
    )
    runner = UserExporter(cfg, mode="export")
    result = runner.export()
    assert result["counts"]["usersExported"] == 1
    assert (runner.output_dir / "users.csv").exists()
    assert (runner.output_dir / "user_groups.csv").exists()
    assert (runner.output_dir / "user_app_links.csv").exists()
    rows = list(csv.DictReader((runner.output_dir / "users.csv").open()))
    assert rows[0]["profile.clientSecret"] == "[REDACTED]"


def test_dry_run_writes_plan(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = ExportConfig(org_url="https://example.okta.com")
    runner = UserExporter(cfg, mode="dry-run")
    plan = runner.dry_run()
    assert plan["willCallOktaApi"] is False
    assert (runner.output_dir / "user_export_plan.json").exists()


def test_login_contains_filter(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("okta_user_exporter.exporter.OktaClient", lambda *args, **kwargs: FakeClient())
    cfg = ExportConfig(
        org_url="https://example.okta.com",
        api_token="token",
        filters=Filters(login_contains="jane"),
        include=Include(groups=False, app_links=False),
    )
    runner = UserExporter(cfg, mode="export")
    result = runner.export()
    assert result["counts"]["usersExported"] == 1
