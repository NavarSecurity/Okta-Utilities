from __future__ import annotations

from pathlib import Path

from okta_backup_validator.reporting import write_outputs


def test_write_outputs(tmp_path: Path) -> None:
    result = {
        "validationId": "okta-backup-validation-20260625T170000Z",
        "generatedAt": "2026-06-25T17:00:00+00:00",
        "backupId": "okta-config-backup-20260625T170000Z",
        "backupDir": "backup",
        "orgUrl": "https://dev-12345678.okta.com",
        "overallStatus": "PASS",
        "summary": {"passed": 1, "warnings": 0, "failures": 0, "totalChecks": 1},
        "checks": [{"severity": "PASS", "code": "TEST", "message": "ok"}],
    }

    outputs = write_outputs(tmp_path, result)

    assert outputs["result"].exists()
    assert outputs["report"].exists()
