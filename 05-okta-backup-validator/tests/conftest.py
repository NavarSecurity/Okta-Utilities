from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


@pytest.fixture
def good_backup(tmp_path: Path) -> Path:
    backup = tmp_path / "backup"
    write_json(
        backup / "manifest.json",
        {
            "utility": "okta-config-backup",
            "version": "0.1.0",
            "backupId": "okta-config-backup-20260625T170000Z",
            "generatedAt": "2026-06-25T17:00:00+00:00",
            "orgUrl": "https://dev-12345678.okta.com",
            "redactionEnabled": True,
            "requestedResources": ["org", "applications", "groups"],
            "files": ["org.json", "applications.json", "groups.json"],
            "counts": {"org": 1, "applications": 1, "groups": 1},
            "warnings": [],
            "errors": [],
            "requestSummary": {"totalRequests": 3, "byStatus": {"200": 3}},
        },
    )
    write_json(backup / "org.json", {"id": "00o123"})
    write_json(backup / "applications.json", [{"id": "0oa123", "label": "App", "name": "oidc_client", "status": "ACTIVE"}])
    write_json(backup / "groups.json", [{"id": "00g123", "profile": {"name": "Group"}}])
    return backup
