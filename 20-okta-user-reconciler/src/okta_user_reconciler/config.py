from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    pass


@dataclass
class MatchRules:
    primary_match_field: str = "login"
    fallback_match_fields: list[str] = field(default_factory=lambda: ["email", "profile.login", "profile.email"])
    case_insensitive: bool = True
    trim_whitespace: bool = True


@dataclass
class Settings:
    ignore_blank_source_values: bool = True
    ignore_blank_target_values: bool = False
    include_source_only: bool = True
    include_target_only: bool = True
    detect_duplicates: bool = True
    strict_mode: bool = False
    ignored_fields: list[str] = field(default_factory=lambda: [
        "id", "created", "activated", "statusChanged", "lastLogin", "lastUpdated",
        "passwordChanged", "_links", "credentials", "type_id", "type", "links"
    ])


@dataclass
class ReconcileConfig:
    source_users_file: Path
    target_users_file: Path
    match_rules: MatchRules
    profile_fields_to_compare: list[str]
    settings: Settings
    config_path: Path


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def _resolve_path(raw: str, config_path: Path) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    return (config_path.parent / p).resolve() if not Path(raw).exists() else Path(raw).resolve()


def load_config(path: str | Path) -> ReconcileConfig:
    config_path = Path(path).resolve()
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")
    try:
        data = json.loads(config_path.read_text())
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Config file is not valid JSON: {exc}") from exc

    source = data.get("sourceUsersFile")
    target = data.get("targetUsersFile")
    if not source:
        raise ConfigError("sourceUsersFile is required")
    if not target:
        raise ConfigError("targetUsersFile is required")

    match_data = data.get("matchRules") or {}
    primary = match_data.get("primaryMatchField", "login")
    if not primary:
        raise ConfigError("matchRules.primaryMatchField cannot be blank")

    fields = data.get("profileFieldsToCompare") or ["login", "email", "firstName", "lastName", "status"]
    if not isinstance(fields, list) or not all(isinstance(x, str) and x.strip() for x in fields):
        raise ConfigError("profileFieldsToCompare must be a list of field names")

    settings_data = data.get("settings") or {}
    settings = Settings(
        ignore_blank_source_values=_as_bool(settings_data.get("ignoreBlankSourceValues"), True),
        ignore_blank_target_values=_as_bool(settings_data.get("ignoreBlankTargetValues"), False),
        include_source_only=_as_bool(settings_data.get("includeSourceOnly"), True),
        include_target_only=_as_bool(settings_data.get("includeTargetOnly"), True),
        detect_duplicates=_as_bool(settings_data.get("detectDuplicates"), True),
        strict_mode=_as_bool(settings_data.get("strictMode"), False),
        ignored_fields=list(settings_data.get("ignoredFields") or Settings().ignored_fields),
    )

    return ReconcileConfig(
        source_users_file=_resolve_path(str(source), config_path),
        target_users_file=_resolve_path(str(target), config_path),
        match_rules=MatchRules(
            primary_match_field=str(primary),
            fallback_match_fields=list(match_data.get("fallbackMatchFields") or []),
            case_insensitive=_as_bool(match_data.get("caseInsensitive"), True),
            trim_whitespace=_as_bool(match_data.get("trimWhitespace"), True),
        ),
        profile_fields_to_compare=[x.strip() for x in fields],
        settings=settings,
        config_path=config_path,
    )
