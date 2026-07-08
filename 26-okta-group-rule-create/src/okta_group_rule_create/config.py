from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from dotenv import load_dotenv


class ConfigError(ValueError):
    pass


from .conditions import resolve_rule_expression  # noqa: E402 - imported after ConfigError to avoid circular import


@dataclass
class Settings:
    skip_existing: bool = True
    require_approved: bool = True
    activate_after_create: bool = False
    continue_on_error: bool = False
    max_rules_per_run: int = 25
    request_timeout_seconds: int = 30
    max_retries: int = 3


@dataclass
class GroupRuleConfig:
    name: str
    description: str = ""
    approved: bool = False
    expression: str = ""
    condition_source: str = "expression"
    basic_condition: Any = None
    target_group_ids: list[str] = field(default_factory=list)
    target_group_names: list[str] = field(default_factory=list)
    exclude_user_ids: list[str] = field(default_factory=list)
    exclude_group_ids: list[str] = field(default_factory=list)
    activate: bool | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class AppConfig:
    target_org_url: str
    api_token: str
    settings: Settings
    rules: list[GroupRuleConfig]


def _read_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(text) or {}
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ConfigError("Config root must be an object.")
    return data


def _clean_org_url(value: str) -> str:
    value = (value or "").strip().rstrip("/")
    if not value:
        return ""
    lowered = value.lower()
    if "-admin.okta" in lowered or "-admin.oktapreview" in lowered or "/admin" in lowered:
        raise ConfigError("Target org URL must not be an Admin Console URL. Use https://your-org.okta.com.")
    if lowered.endswith("/api/v1") or "/api/v1/" in lowered:
        raise ConfigError("Target org URL must be the base org URL, not an /api/v1 URL.")
    if not (lowered.startswith("https://") or lowered.startswith("http://")):
        raise ConfigError("Target org URL must start with https://.")
    return value


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "y", "1", "approved"}
    return bool(value)


def _as_string_list(value: Any, field_name: str) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        result = []
        for item in value:
            if item in (None, ""):
                continue
            result.append(str(item).strip())
        return result
    raise ConfigError(f"{field_name} must be a string or list of strings.")


def load_config(config_path: str | Path) -> AppConfig:
    load_dotenv()
    path = Path(config_path)
    data = _read_file(path)

    env_url = os.getenv("OKTA_TARGET_ORG_URL", "").strip()
    env_token = os.getenv("OKTA_API_TOKEN", "").strip()

    target_org_url = _clean_org_url(env_url or data.get("targetOrgUrl", ""))
    api_token = env_token or str(data.get("apiToken", "")).strip()

    if not target_org_url:
        raise ConfigError("Missing target org URL. Set OKTA_TARGET_ORG_URL or targetOrgUrl.")
    if not api_token:
        raise ConfigError("Missing Okta API token. Set OKTA_API_TOKEN in .env.")

    settings_data = data.get("settings") or {}
    settings = Settings(
        skip_existing=bool(settings_data.get("skipExisting", True)),
        require_approved=bool(settings_data.get("requireApproved", True)),
        activate_after_create=bool(settings_data.get("activateAfterCreate", False)),
        continue_on_error=bool(settings_data.get("continueOnError", False)),
        max_rules_per_run=int(settings_data.get("maxRulesPerRun", 25)),
        request_timeout_seconds=int(settings_data.get("requestTimeoutSeconds", 30)),
        max_retries=int(settings_data.get("maxRetries", 3)),
    )

    if settings.max_rules_per_run <= 0:
        raise ConfigError("settings.maxRulesPerRun must be greater than zero.")

    rules_data = data.get("rules") or []
    if not isinstance(rules_data, list):
        raise ConfigError("rules must be a list.")
    if len(rules_data) > settings.max_rules_per_run:
        raise ConfigError(f"Config contains {len(rules_data)} rules, which exceeds maxRulesPerRun={settings.max_rules_per_run}.")

    rules: list[GroupRuleConfig] = []
    for index, item in enumerate(rules_data, start=1):
        if not isinstance(item, dict):
            raise ConfigError(f"Rule #{index} must be an object.")
        name = str(item.get("name", "")).strip()
        if not name:
            raise ConfigError(f"Rule #{index} is missing name.")
        expression, condition_source, basic_condition = resolve_rule_expression(item, name)
        target_group_ids = _as_string_list(item.get("targetGroupIds", []), "targetGroupIds")
        target_group_names = _as_string_list(item.get("targetGroupNames", []), "targetGroupNames")
        if not target_group_ids and not target_group_names:
            raise ConfigError(f"Rule {name!r} must include targetGroupIds or targetGroupNames.")
        activate_raw = item.get("activate", None)
        activate = None if activate_raw is None else _as_bool(activate_raw)
        rules.append(
            GroupRuleConfig(
                name=name,
                description=str(item.get("description", "")).strip(),
                approved=_as_bool(item.get("approved", False)),
                expression=expression,
                condition_source=condition_source,
                basic_condition=basic_condition,
                target_group_ids=target_group_ids,
                target_group_names=target_group_names,
                exclude_user_ids=_as_string_list(item.get("excludeUserIds", []), "excludeUserIds"),
                exclude_group_ids=_as_string_list(item.get("excludeGroupIds", []), "excludeGroupIds"),
                activate=activate,
                raw=item,
            )
        )

    return AppConfig(
        target_org_url=target_org_url,
        api_token=api_token,
        settings=settings,
        rules=rules,
    )
