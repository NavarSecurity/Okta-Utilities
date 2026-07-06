import csv
from pathlib import Path

from okta_user_bulk_importer.config import ImportSettings, UserImportConfig
from okta_user_bulk_importer.importer import UserBulkImporter, redact_payload


def make_cfg(csv_path: Path, **settings):
    return UserImportConfig(
        targetOrgUrl="https://example.okta.com",
        apiToken="token",
        inputUserCsv=str(csv_path),
        settings=ImportSettings(performDuplicateCheckInDryRun=False, **settings),
    )


def write_csv(path: Path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["login", "email", "firstName", "lastName", "department", "groupIds", "password"])
        writer.writeheader()
        writer.writerows(rows)


def test_dry_run_builds_plan(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "users.csv"
    write_csv(csv_path, [{"login": "alex@example.com", "email": "alex@example.com", "firstName": "Alex", "lastName": "Test", "department": "IT", "groupIds": "", "password": ""}])
    importer = UserBulkImporter(make_cfg(csv_path), "dry-run")
    result = importer.run()
    assert result["summary"]["plannedRows"] == 1
    assert result["summary"]["failedUsers"] == 0
    assert (importer.output_dir / "user_import_plan.json").exists()


def test_missing_required_field_fails_row(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "users.csv"
    write_csv(csv_path, [{"login": "bad@example.com", "email": "bad@example.com", "firstName": "", "lastName": "Test", "department": "IT", "groupIds": "", "password": ""}])
    importer = UserBulkImporter(make_cfg(csv_path), "dry-run")
    result = importer.run()
    assert result["summary"]["failedUsers"] == 1
    assert "firstName" in result["failedUsers"][0]["errors"]


def test_group_ids_from_default_and_row(tmp_path):
    csv_path = tmp_path / "users.csv"
    write_csv(csv_path, [{"login": "alex@example.com", "email": "alex@example.com", "firstName": "Alex", "lastName": "Test", "department": "IT", "groupIds": "00g2;00g3", "password": ""}])
    cfg = make_cfg(csv_path)
    cfg.defaultGroupIds = ["00g1", "00g2"]
    importer = UserBulkImporter(cfg, "dry-run")
    assert importer._groups_for_row({"groupIds": "00g2;00g3"}) == ["00g1", "00g2", "00g3"]


def test_redacts_password_values():
    data = {"credentials": {"password": {"value": "Secret123"}}, "profile": {"login": "a@example.com"}}
    redacted = redact_payload(data)
    assert redacted["credentials"]["password"] == "[REDACTED]"
    assert redacted["profile"]["login"] == "a@example.com"
