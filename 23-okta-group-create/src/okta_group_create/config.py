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
class Settings:
    skip_existing: bool = True
    require_approved: bool = False
    approved_values: list[str] = field(default_factory=lambda: ["true", "yes", "y", "approved"])
    continue_on_error: bool = False
    max_groups_per_run: int = 100
    request_timeout_seconds: int = 30
    max_retries: int = 3
    retry_backoff_seconds: int = 2


@dataclass
class GroupCreateConfig:
    target_org_url: str
    api_token: str | None
    groups_file: Path
    settings: Settings
    columns: dict[str, str]
    profile_field_mappings: dict[str, str]
    raw: dict[str, Any]


def normalize_org_url(url: str) -> str:
    normalized = (url or "").strip().rstrip("/")
    if not normalized:
        raise ConfigError("targetOrgUrl is required through config or OKTA_TARGET_ORG_URL.")
    lower = normalized.lower()
    if "-admin.okta.com" in lower or "-admin.oktapreview.com" in lower or lower.endswith("/admin"):
        raise ConfigError("Use the normal Okta org URL, not the Admin Console URL. Example: https://your-org.okta.com")
    if "/api/" in lower:
        raise ConfigError("Use the Okta org base URL only. Do not include /api paths.")
    if not (lower.startswith("https://") or lower.startswith("http://localhost")):
        raise ConfigError("targetOrgUrl must start with https:// for Okta orgs.")
    return normalized


def load_config(config_path: str | Path) -> GroupCreateConfig:
    load_dotenv()
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))

    env_url = os.getenv("OKTA_TARGET_ORG_URL", "").strip()
    target_org_url = normalize_org_url(env_url or data.get("targetOrgUrl", ""))
    api_token = os.getenv("OKTA_API_TOKEN") or data.get("apiToken")

    groups_file_value = data.get("groupsFile") or data.get("inputFile")
    if not groups_file_value:
        raise ConfigError("groupsFile is required.")
    groups_file = Path(groups_file_value)

    settings_data = data.get("settings", {}) or {}
    settings = Settings(
        skip_existing=bool(settings_data.get("skipExisting", True)),
        require_approved=bool(settings_data.get("requireApproved", False)),
        approved_values=[str(v).lower() for v in settings_data.get("approvedValues", ["true", "yes", "y", "approved"])],
        continue_on_error=bool(settings_data.get("continueOnError", False)),
        max_groups_per_run=int(settings_data.get("maxGroupsPerRun", 100)),
        request_timeout_seconds=int(settings_data.get("requestTimeoutSeconds", 30)),
        max_retries=int(settings_data.get("maxRetries", 3)),
        retry_backoff_seconds=int(settings_data.get("retryBackoffSeconds", 2)),
    )
    if settings.max_groups_per_run < 1:
        raise ConfigError("maxGroupsPerRun must be at least 1.")

    columns = data.get("columns") or {"name": "name", "description": "description", "approved": "approved"}
    profile_field_mappings = data.get("profileFieldMappings") or {"name": "name", "description": "description"}
    if "name" not in profile_field_mappings:
        profile_field_mappings["name"] = columns.get("name", "name")

    return GroupCreateConfig(
        target_org_url=target_org_url,
        api_token=api_token,
        groups_file=groups_file,
        settings=settings,
        columns=columns,
        profile_field_mappings=profile_field_mappings,
        raw=data,
    )
