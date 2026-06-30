from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


class ConfigError(ValueError):
    pass


@dataclass
class AppClonerConfig:
    source_backup_dir: Path
    target_org_url: str
    target_api_token: str
    output_dir: Path = Path("output")
    selection: dict[str, Any] = field(default_factory=dict)
    skip_existing: bool = True
    clone_inactive_apps: bool = False
    activate_cloned_apps: bool = False
    include_assignments: bool = False
    include_provisioning_settings: bool = False
    fail_fast: bool = False
    page_limit: int = 200
    timeout_seconds: int = 30
    max_retries: int = 4
    retry_base_seconds: float = 1.0
    redaction_enabled: bool = True


def _normalize_keys(data: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "sourceBackupDir": "source_backup_dir",
        "targetOrgUrl": "target_org_url",
        "targetApiToken": "target_api_token",
        "outputDir": "output_dir",
        "skipExisting": "skip_existing",
        "cloneInactiveApps": "clone_inactive_apps",
        "activateClonedApps": "activate_cloned_apps",
        "includeAssignments": "include_assignments",
        "includeProvisioningSettings": "include_provisioning_settings",
        "failFast": "fail_fast",
        "pageLimit": "page_limit",
        "timeoutSeconds": "timeout_seconds",
        "maxRetries": "max_retries",
        "retryBaseSeconds": "retry_base_seconds",
        "redactionEnabled": "redaction_enabled",
    }
    return {aliases.get(k, k): v for k, v in data.items()}


def load_config(path: str | Path) -> AppClonerConfig:
    load_dotenv()
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON config: {exc}") from exc

    data = _normalize_keys(raw)

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

    return AppClonerConfig(
        source_backup_dir=source_backup_dir,
        target_org_url=target_org_url,
        target_api_token=target_api_token,
        output_dir=Path(data.get("output_dir", "output")),
        selection=data.get("selection") or {},
        skip_existing=bool(data.get("skip_existing", True)),
        clone_inactive_apps=bool(data.get("clone_inactive_apps", False)),
        activate_cloned_apps=bool(data.get("activate_cloned_apps", False)),
        include_assignments=bool(data.get("include_assignments", False)),
        include_provisioning_settings=bool(data.get("include_provisioning_settings", False)),
        fail_fast=bool(data.get("fail_fast", False)),
        page_limit=int(data.get("page_limit", 200)),
        timeout_seconds=int(data.get("timeout_seconds", 30)),
        max_retries=int(data.get("max_retries", 4)),
        retry_base_seconds=float(data.get("retry_base_seconds", 1.0)),
        redaction_enabled=bool(data.get("redaction_enabled", True)),
    )
