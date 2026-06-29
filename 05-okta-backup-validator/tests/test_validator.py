from __future__ import annotations

import json
from pathlib import Path

from okta_backup_validator.config import ValidatorConfig
from okta_backup_validator.validator import BackupValidator


def test_good_backup_passes(good_backup: Path, tmp_path: Path) -> None:
    cfg = ValidatorConfig(backup_dir=good_backup, output_dir=tmp_path / "out")
    result = BackupValidator(cfg).run()

    assert result["overallStatus"] == "PASS"
    assert result["summary"]["failures"] == 0


def test_placeholder_org_url_fails(good_backup: Path, tmp_path: Path) -> None:
    manifest_path = good_backup / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["orgUrl"] = "https://your-org.okta.com"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    cfg = ValidatorConfig(backup_dir=good_backup, output_dir=tmp_path / "out")
    result = BackupValidator(cfg).run()

    assert result["overallStatus"] == "FAIL"
    assert any(check["code"] == "ORG_URL_INVALID_OR_PLACEHOLDER" for check in result["checks"])


def test_manifest_count_mismatch_fails(good_backup: Path, tmp_path: Path) -> None:
    manifest_path = good_backup / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["counts"]["applications"] = 99
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    cfg = ValidatorConfig(backup_dir=good_backup, output_dir=tmp_path / "out")
    result = BackupValidator(cfg).run()

    assert result["overallStatus"] == "FAIL"
    assert any(check["code"] == "COUNT_MISMATCH" for check in result["checks"])


def test_manifest_errors_warn_by_default(good_backup: Path, tmp_path: Path) -> None:
    manifest_path = good_backup / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["errors"] = [{"resource": "domains", "message": "not available"}]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    cfg = ValidatorConfig(backup_dir=good_backup, output_dir=tmp_path / "out")
    result = BackupValidator(cfg).run()

    assert result["overallStatus"] == "WARN"
    assert any(check["code"] == "MANIFEST_RECORDED_ERRORS" and check["severity"] == "WARN" for check in result["checks"])


def test_strict_mode_fails_on_manifest_errors(good_backup: Path, tmp_path: Path) -> None:
    manifest_path = good_backup / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["errors"] = [{"resource": "domains", "message": "not available"}]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    cfg = ValidatorConfig(backup_dir=good_backup, output_dir=tmp_path / "out", strict_mode=True, require_no_resource_errors=True)
    result = BackupValidator(cfg).run()

    assert result["overallStatus"] == "FAIL"
    assert any(check["code"] == "MANIFEST_RECORDED_ERRORS" and check["severity"] == "FAIL" for check in result["checks"])


def test_sensitive_value_scan_fails(good_backup: Path, tmp_path: Path) -> None:
    app_path = good_backup / "applications.json"
    apps = json.loads(app_path.read_text())
    apps[0]["client_secret"] = "plain-secret-value"
    app_path.write_text(json.dumps(apps), encoding="utf-8")

    cfg = ValidatorConfig(backup_dir=good_backup, output_dir=tmp_path / "out")
    result = BackupValidator(cfg).run()

    assert result["overallStatus"] == "FAIL"
    assert any(check["code"] == "SENSITIVE_VALUES_FOUND" for check in result["checks"])


def test_domains_wrapped_response_is_validated_as_domain_records(tmp_path: Path) -> None:
    backup = tmp_path / "backup"
    backup.mkdir()
    (backup / "manifest.json").write_text(
        json.dumps(
            {
                "utility": "okta-config-backup",
                "version": "0.1.1",
                "backupId": "okta-config-backup-20260625T180000Z",
                "generatedAt": "2026-06-25T18:00:00+00:00",
                "orgUrl": "https://dev-12345678.okta.com",
                "redactionEnabled": True,
                "requestedResources": ["domains"],
                "files": ["domains.json"],
                "counts": {"domains": 1},
                "warnings": [],
                "errors": [],
                "requestSummary": {"totalRequests": 1, "byStatus": {"200": 1}},
            }
        ),
        encoding="utf-8",
    )
    (backup / "domains.json").write_text(
        json.dumps(
            [
                {
                    "domains": [
                        {
                            "id": "default",
                            "domain": "integrator-1703705.okta.com",
                            "brandId": "bnd14igebbg02N8Vf698",
                            "certificateSourceType": "OKTA_MANAGED",
                            "validationStatus": "COMPLETED",
                        }
                    ]
                }
            ]
        ),
        encoding="utf-8",
    )

    cfg = ValidatorConfig(backup_dir=backup, output_dir=tmp_path / "out")
    result = BackupValidator(cfg).run()

    assert result["overallStatus"] == "PASS"
    assert not any(check["code"] == "RESOURCE_REQUIRED_FIELDS_MISSING" for check in result["checks"])
    assert any(
        check["code"] == "COUNT_MATCHES_MANIFEST" and check.get("resource") == "domains"
        for check in result["checks"]
    )


def test_domains_dict_wrapper_count_and_fields_are_valid(tmp_path: Path) -> None:
    backup = tmp_path / "backup"
    backup.mkdir()
    (backup / "manifest.json").write_text(
        json.dumps(
            {
                "utility": "okta-config-backup",
                "version": "0.1.1",
                "backupId": "okta-config-backup-20260625T180500Z",
                "generatedAt": "2026-06-25T18:05:00+00:00",
                "orgUrl": "https://dev-12345678.okta.com",
                "redactionEnabled": True,
                "requestedResources": ["domains"],
                "files": ["domains.json"],
                "counts": {"domains": 2},
                "warnings": [],
                "errors": [],
                "requestSummary": {"totalRequests": 1, "byStatus": {"200": 1}},
            }
        ),
        encoding="utf-8",
    )
    (backup / "domains.json").write_text(
        json.dumps(
            {
                "domains": [
                    {"id": "default", "domain": "dev-12345678.okta.com"},
                    {"id": "custom", "domain": "login.example.com"},
                ]
            }
        ),
        encoding="utf-8",
    )

    cfg = ValidatorConfig(backup_dir=backup, output_dir=tmp_path / "out")
    result = BackupValidator(cfg).run()

    assert result["overallStatus"] == "PASS"
    assert any(
        check["code"] == "RESOURCE_REQUIRED_FIELDS_PRESENT" and check.get("resource") == "domains"
        for check in result["checks"]
    )


def test_sensitive_scan_ignores_okta_structural_keys(tmp_path: Path) -> None:
    backup = tmp_path / "backup"
    backup.mkdir()
    (backup / "manifest.json").write_text(
        json.dumps(
            {
                "utility": "okta-config-backup",
                "version": "0.1.2",
                "backupId": "okta-config-backup-20260625T181000Z",
                "generatedAt": "2026-06-25T18:10:00+00:00",
                "orgUrl": "https://dev-12345678.okta.com",
                "redactionEnabled": True,
                "requestedResources": ["authorization_servers", "policies"],
                "files": ["authorization_servers.json", "policies.json"],
                "counts": {"authorization_servers": 0, "policies": 1},
                "warnings": [],
                "errors": [],
                "requestSummary": {"totalRequests": 2, "byStatus": {"200": 2}},
            }
        ),
        encoding="utf-8",
    )
    (backup / "authorization_servers.json").write_text(
        json.dumps({"authorizationServers": [], "detailsByAuthorizationServerId": {}}),
        encoding="utf-8",
    )
    (backup / "policies.json").write_text(
        json.dumps(
            {
                "policyTypes": {
                    "PASSWORD": {
                        "errors": [],
                        "policies": [
                            {
                                "id": "00p123",
                                "name": "Default Policy",
                                "type": "PASSWORD",
                                "status": "ACTIVE",
                                "settings": {"password": "[REDACTED]"},
                            }
                        ],
                        "rulesByPolicyId": {
                            "00p123": [
                                {
                                    "actions": {
                                        "passwordChange": {"access": "ALLOW"},
                                        "selfServicePasswordReset": {"access": "ALLOW"},
                                    }
                                }
                            ]
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    cfg = ValidatorConfig(backup_dir=backup, output_dir=tmp_path / "out")
    result = BackupValidator(cfg).run()

    assert result["overallStatus"] == "PASS"
    assert not any(check["code"] == "SENSITIVE_VALUES_FOUND" for check in result["checks"])


def test_sensitive_value_scan_reports_exact_value(good_backup: Path, tmp_path: Path) -> None:
    app_path = good_backup / "applications.json"
    apps = json.loads(app_path.read_text())
    apps[0]["client_secret"] = "plain-secret-value"
    app_path.write_text(json.dumps(apps), encoding="utf-8")

    cfg = ValidatorConfig(backup_dir=good_backup, output_dir=tmp_path / "out")
    result = BackupValidator(cfg).run()

    sensitive_checks = [check for check in result["checks"] if check["code"] == "SENSITIVE_VALUES_FOUND"]
    assert sensitive_checks
    findings = sensitive_checks[0]["details"]["findings"]
    assert findings[0]["value"] == "plain-secret-value"
    assert findings[0]["value_preview"] == "plain-secret-value"
