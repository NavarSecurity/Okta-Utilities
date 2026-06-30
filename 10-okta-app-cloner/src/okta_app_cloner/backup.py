from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class BackupError(ValueError):
    pass


def read_json(path: Path) -> Any:
    if not path.exists():
        raise BackupError(f"Required backup file not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BackupError(f"Invalid JSON in {path}: {exc}") from exc


def load_applications(source_backup_dir: Path) -> list[dict[str, Any]]:
    data = read_json(source_backup_dir / "applications.json")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("applications", "apps", "items"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    raise BackupError("applications.json must be a list of application objects or contain an applications list.")
