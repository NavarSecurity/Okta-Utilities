from __future__ import annotations

from pathlib import Path
from typing import Any
import json

RESOURCE_FILE_MAP = {
    "org": "org.json",
    "applications": "applications.json",
    "groups": "groups.json",
    "group_rules": "group_rules.json",
    "policies": "policies.json",
    "identity_providers": "identity_providers.json",
    "authorization_servers": "authorization_servers.json",
    "trusted_origins": "trusted_origins.json",
    "network_zones": "network_zones.json",
    "domains": "domains.json",
    "brands": "brands.json",
    "authenticators": "authenticators.json",
    "event_hooks": "event_hooks.json",
    "inline_hooks": "inline_hooks.json",
}


def load_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_resource(backup_dir: Path, resource: str) -> tuple[Any | None, str | None]:
    filename = RESOURCE_FILE_MAP.get(resource, f"{resource}.json")
    path = backup_dir / filename
    if not path.exists():
        return None, f"Missing file: {filename}"
    try:
        return load_json_file(path), None
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON in {filename}: {exc}"


def validate_backup_dir(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} backup directory not found: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"{label} backup path is not a directory: {path}")
