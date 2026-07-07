from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv


class ConfigError(ValueError):
    pass


@dataclass
class LoaderConfig:
    target_org_url: str
    membership_file: str
    input_format: str = "auto"
    default_action: str = "add"
    settings: dict[str, Any] = field(default_factory=dict)
    safety: dict[str, Any] = field(default_factory=dict)
    columns: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        default_settings = {
            "continueOnError": False,
            "requestTimeoutSeconds": 30,
            "maxRetries": 3,
            "retryBackoffSeconds": 2,
            "verifyExistingStateInDryRun": True,
        }
        default_settings.update(self.settings or {})
        self.settings = default_settings

        default_safety = {
            "requireApproved": True,
            "approvedValues": ["true", "yes", "y", "approved"],
            "requireReason": True,
            "maxChangesPerRun": 250,
            "allowRemove": False,
            "allowReplace": False,
            "skipExistingAdditions": True,
            "skipMissingRemovals": True,
            "allowGroupNameLookup": True,
            "allowUserLoginLookup": True,
            "blockAdminUsers": True,
            "protectedLoginPatterns": ["admin", "breakglass", "break-glass", "service", "svc-"],
        }
        default_safety.update(self.safety or {})
        self.safety = default_safety

        default_columns = {
            "groupId": "groupId",
            "groupName": "groupName",
            "userId": "userId",
            "login": "login",
            "email": "email",
            "action": "action",
            "approved": "approved",
            "reason": "reason",
        }
        default_columns.update(self.columns or {})
        self.columns = default_columns


def _clean_url(value: str) -> str:
    cleaned = (value or "").strip().rstrip("/")
    if not cleaned:
        return cleaned
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigError("targetOrgUrl must be a full Okta org URL such as https://your-org.okta.com")
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/").lower()
    if "-admin.okta" in host or "-admin.oktapreview" in host:
        raise ConfigError("Do not use the Okta Admin Console URL. Use the normal org URL, for example https://your-org.okta.com")
    if path in {"/admin", "/api", "/api/v1"} or path.startswith("/admin/") or path.startswith("/api/"):
        raise ConfigError("targetOrgUrl must be the base org URL only. Do not include /admin or /api/v1")
    return f"{parsed.scheme}://{parsed.netloc}"


def load_config(config_path: str | Path) -> LoaderConfig:
    load_dotenv()
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    env_org = os.getenv("OKTA_TARGET_ORG_URL", "").strip()
    target_org_url = _clean_url(env_org or raw.get("targetOrgUrl", ""))
    if not target_org_url:
        raise ConfigError("targetOrgUrl is required in config or OKTA_TARGET_ORG_URL is required in .env")

    membership_file = raw.get("membershipFile") or raw.get("input", {}).get("membershipFile")
    if not membership_file:
        raise ConfigError("membershipFile is required")

    input_format = raw.get("inputFormat") or raw.get("input", {}).get("format", "auto")
    default_action = str(raw.get("defaultAction") or raw.get("defaults", {}).get("action", "add")).lower().strip()
    if default_action not in {"add", "remove", "replace"}:
        raise ConfigError("defaultAction must be add, remove, or replace")

    settings = {
        "continueOnError": False,
        "requestTimeoutSeconds": 30,
        "maxRetries": 3,
        "retryBackoffSeconds": 2,
        "verifyExistingStateInDryRun": True,
    }
    settings.update(raw.get("settings", {}))

    safety = {
        "requireApproved": True,
        "approvedValues": ["true", "yes", "y", "approved"],
        "requireReason": True,
        "maxChangesPerRun": 250,
        "allowRemove": False,
        "allowReplace": False,
        "skipExistingAdditions": True,
        "skipMissingRemovals": True,
        "allowGroupNameLookup": True,
        "allowUserLoginLookup": True,
        "blockAdminUsers": True,
        "protectedLoginPatterns": ["admin", "breakglass", "break-glass", "service", "svc-"],
    }
    safety.update(raw.get("safety", {}))

    columns = {
        "groupId": "groupId",
        "groupName": "groupName",
        "userId": "userId",
        "login": "login",
        "email": "email",
        "action": "action",
        "approved": "approved",
        "reason": "reason",
    }
    columns.update(raw.get("columns", {}))

    return LoaderConfig(
        target_org_url=target_org_url,
        membership_file=str(membership_file),
        input_format=str(input_format).lower(),
        default_action=default_action,
        settings=settings,
        safety=safety,
        columns=columns,
    )
