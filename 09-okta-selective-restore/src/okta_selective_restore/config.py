from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

SUPPORTED_RESOURCES = {
    "groups",
    "applications",
    "trusted_origins",
    "network_zones",
    "authorization_servers",
}

UNSUPPORTED_BUT_KNOWN = {
    "org",
    "group_rules",
    "policies",
    "identity_providers",
    "event_hooks",
    "inline_hooks",
    "brands",
    "domains",
    "authenticators",
}


class ConfigError(ValueError):
    pass


@dataclass
class RestoreConfig:
    source_backup_dir: Path
    target_org_url: str
    target_api_token: str
    output_dir: Path = Path("output")
    include: list[str] = field(default_factory=lambda: sorted(SUPPORTED_RESOURCES))
    selection: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    skip_existing: bool = True
    restore_inactive_objects: bool = False
    activate_apps: bool = False
    fail_fast: bool = False
    page_limit: int = 200
    timeout_seconds: int = 30
    max_retries: int = 4
    retry_base_seconds: float = 1.0
    redaction_enabled: bool = True


def _camel_to_snake_config(data: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "sourceBackupDir": "source_backup_dir",
        "targetOrgUrl": "target_org_url",
        "outputDir": "output_dir",
        "skipExisting": "skip_existing",
        "restoreInactiveObjects": "restore_inactive_objects",
        "activateApps": "activate_apps",
        "failFast": "fail_fast",
        "pageLimit": "page_limit",
        "timeoutSeconds": "timeout_seconds",
        "maxRetries": "max_retries",
        "retryBaseSeconds": "retry_base_seconds",
        "redactionEnabled": "redaction_enabled",
    }
    normalized: dict[str, Any] = {}
    for key, value in data.items():
        normalized[aliases.get(key, key)] = value
    return normalized


def load_config(path: str | Path) -> RestoreConfig:
    load_dotenv()
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON config: {exc}") from exc

    data = _camel_to_snake_config(raw)

    target_org_url = (
        os.getenv("OKTA_TARGET_ORG_URL")
        or os.getenv("OKTA_ORG_URL")
        or data.get("target_org_url")
        or ""
    ).strip().rstrip("/")
    target_api_token = (
        os.getenv("OKTA_TARGET_API_TOKEN")
        or os.getenv("OKTA_API_TOKEN")
        or data.get("target_api_token")
        or ""
    ).strip()

    if not target_org_url.startswith("https://"):
        raise ConfigError("Target Okta org URL must start with https://")
    if "/api/" in target_org_url or target_org_url.endswith("/admin") or "/admin/" in target_org_url:
        raise ConfigError("Target Okta org URL must be the base org URL only, for example https://dev-12345678.okta.com")
    if not target_api_token:
        raise ConfigError("Target Okta API token is required. Set OKTA_TARGET_API_TOKEN in .env or environment variables.")
    if target_api_token.upper().startswith("SSWS "):
        raise ConfigError("Do not include the literal 'SSWS' prefix in OKTA_TARGET_API_TOKEN. Use only the token value.")

    source_backup_dir = Path(data.get("source_backup_dir", "input/source-backup"))
    if not source_backup_dir.exists():
        raise ConfigError(f"Source backup directory not found: {source_backup_dir}")

    include = data.get("include") or sorted(SUPPORTED_RESOURCES)
    if isinstance(include, str):
        include = [part.strip() for part in include.split(",") if part.strip()]
    include = [str(x).strip() for x in include]

    unknown = sorted(set(include) - SUPPORTED_RESOURCES - UNSUPPORTED_BUT_KNOWN)
    if unknown:
        raise ConfigError(f"Unknown resource type(s): {', '.join(unknown)}")

    return RestoreConfig(
        source_backup_dir=source_backup_dir,
        target_org_url=target_org_url,
        target_api_token=target_api_token,
        output_dir=Path(data.get("output_dir", "output")),
        include=include,
        selection=data.get("selection") or {},
        skip_existing=bool(data.get("skip_existing", True)),
        restore_inactive_objects=bool(data.get("restore_inactive_objects", False)),
        activate_apps=bool(data.get("activate_apps", False)),
        fail_fast=bool(data.get("fail_fast", False)),
        page_limit=int(data.get("page_limit", 200)),
        timeout_seconds=int(data.get("timeout_seconds", 30)),
        max_retries=int(data.get("max_retries", 4)),
        retry_base_seconds=float(data.get("retry_base_seconds", 1.0)),
        redaction_enabled=bool(data.get("redaction_enabled", True)),
    )
