from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    pass


@dataclass
class InputConfig:
    user_ids: list[str] = field(default_factory=list)
    user_logins: list[str] = field(default_factory=list)
    group_ids: list[str] = field(default_factory=list)
    group_names: list[str] = field(default_factory=list)
    statuses: list[str] = field(default_factory=lambda: ["ACTIVE"])
    include_users_without_factors: bool = True


@dataclass
class ReportingConfig:
    required_factor_types: list[str] = field(default_factory=list)
    factor_types: list[str] = field(default_factory=list)
    include_factor_profile: bool = False
    include_raw_factors: bool = False


@dataclass
class SettingsConfig:
    page_limit: int = 200
    request_timeout_seconds: int = 30
    max_retries: int = 3
    redact_sensitive_profile_values: bool = True


@dataclass
class AppConfig:
    org_url: str
    api_token: str
    input: InputConfig
    reporting: ReportingConfig
    settings: SettingsConfig
    config_path: Path


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _as_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ConfigError(f"{field_name} must be a list.")
    return [str(item).strip() for item in value if str(item).strip()]


def normalize_org_url(value: str) -> str:
    org_url = (value or "").strip().rstrip("/")
    if not org_url:
        raise ConfigError("Okta org URL is required. Set OKTA_ORG_URL or orgUrl in config.")
    if not org_url.startswith("https://"):
        raise ConfigError("Okta org URL must start with https://")
    if "/admin" in org_url or "/api/v1" in org_url or "/oauth2" in org_url:
        raise ConfigError("Use the base Okta org URL only, not /admin, /api/v1, or /oauth2 paths.")
    host = org_url.split("https://", 1)[1].split("/", 1)[0]
    if re.search(r"-admin\.okta(preview)?\.com$", host):
        raise ConfigError("Do not use the Okta Admin Console URL. Use the base org URL such as https://example.okta.com")
    return org_url


def load_config(config_path: str | Path) -> AppConfig:
    load_dotenv()
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))

    org_url = normalize_org_url(os.getenv("OKTA_ORG_URL") or data.get("orgUrl") or "")
    api_token = os.getenv("OKTA_API_TOKEN") or data.get("apiToken") or ""
    api_token = api_token.strip()
    if not api_token or api_token == "replace-with-okta-api-token":
        raise ConfigError("Okta API token is required. Set OKTA_API_TOKEN in .env.")

    raw_input = data.get("input") or {}
    raw_reporting = data.get("reporting") or {}
    raw_settings = data.get("settings") or {}

    input_cfg = InputConfig(
        user_ids=_as_list(raw_input.get("userIds"), "input.userIds"),
        user_logins=_as_list(raw_input.get("userLogins"), "input.userLogins"),
        group_ids=_as_list(raw_input.get("groupIds"), "input.groupIds"),
        group_names=_as_list(raw_input.get("groupNames"), "input.groupNames"),
        statuses=[s.upper() for s in _as_list(raw_input.get("statuses", ["ACTIVE"]), "input.statuses")],
        include_users_without_factors=bool(raw_input.get("includeUsersWithoutFactors", True)),
    )

    reporting_cfg = ReportingConfig(
        required_factor_types=_as_list(raw_reporting.get("requiredFactorTypes", []), "reporting.requiredFactorTypes"),
        factor_types=_as_list(raw_reporting.get("factorTypes", []), "reporting.factorTypes"),
        include_factor_profile=bool(raw_reporting.get("includeFactorProfile", False)),
        include_raw_factors=bool(raw_reporting.get("includeRawFactors", False)),
    )

    page_limit = int(raw_settings.get("pageLimit", 200))
    if page_limit < 1 or page_limit > 200:
        raise ConfigError("settings.pageLimit must be between 1 and 200.")

    settings_cfg = SettingsConfig(
        page_limit=page_limit,
        request_timeout_seconds=int(raw_settings.get("requestTimeoutSeconds", 30)),
        max_retries=int(raw_settings.get("maxRetries", 3)),
        redact_sensitive_profile_values=bool(raw_settings.get("redactSensitiveProfileValues", True)),
    )

    return AppConfig(
        org_url=org_url,
        api_token=api_token,
        input=input_cfg,
        reporting=reporting_cfg,
        settings=settings_cfg,
        config_path=path,
    )
