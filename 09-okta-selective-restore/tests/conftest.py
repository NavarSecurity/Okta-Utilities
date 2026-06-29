from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def sample_backup_dir(tmp_path: Path) -> Path:
    backup = tmp_path / "backup"
    backup.mkdir()
    (backup / "groups.json").write_text(
        json.dumps(
            [
                {
                    "id": "00g1",
                    "type": "OKTA_GROUP",
                    "created": "2026-01-01T00:00:00.000Z",
                    "profile": {"name": "Engineering", "description": "Eng group"},
                    "_links": {"self": {"href": "https://example.okta.com/api/v1/groups/00g1"}},
                },
                {
                    "id": "00g2",
                    "type": "OKTA_GROUP",
                    "status": "INACTIVE",
                    "profile": {"name": "Inactive Group", "description": "Skip me"},
                },
            ]
        ),
        encoding="utf-8",
    )
    (backup / "trusted_origins.json").write_text(
        json.dumps(
            [
                {
                    "id": "to1",
                    "name": "App Origin",
                    "origin": "https://app.example.com",
                    "scopes": [{"type": "CORS"}],
                    "status": "ACTIVE",
                    "_links": {"self": {"href": "x"}},
                }
            ]
        ),
        encoding="utf-8",
    )
    return backup
