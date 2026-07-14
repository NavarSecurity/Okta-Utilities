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
class AppSelection:
    mode: str = "all"
    app_ids: list[str] = field(default_factory=list)
    app_names: list[str] = field(default_factory=list)
    app_file: str = "input/apps.txt"


DEFAULT_EXCLUDED_APP_NAMES = [
    "saasure",
    "okta_enduser",
    "okta_browser_plugin",
    "okta_oin_submission_tester_app",
    "okta_iga_reviewer",
]


@dataclass
class ExportConfig:
    output_directory: str = "output"
    include_user_schemas: bool = True
    user_schema_ids: list[str] = field(default_factory=lambda: ["default"])
    include_group_schema: bool = False
    include_app_schemas: bool = True
    app_selection: AppSelection = field(default_factory=AppSelection)
    include_inactive_apps: bool = False
    skip_okta_system_apps: bool = True
    excluded_app_names: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDED_APP_NAMES))
    continue_on_app_schema_error: bool = True
    write_individual_schema_files: bool = True
    redact_sensitive_values: bool = True
    timeout_seconds: int = 30
    max_retries: int = 3
    okta_org_url: str | None = None
    okta_api_token: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ConfigError(f"Expected boolean value, got {value!r}")


def _as_list(value: Any, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{name} must be a list of strings")
    return value


def _normalize_org_url(url: str | None) -> str | None:
    if not url:
        return None
    normalized = url.strip().rstrip("/")
    if normalized.endswith("/api/v1"):
        normalized = normalized[: -len("/api/v1")]
    return normalized


def load_config(config_path: str | Path) -> ExportConfig:
    load_dotenv()
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in config file: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError("Config file must contain a JSON object")

    selection_raw = data.get("appSelection") or {}
    if not isinstance(selection_raw, dict):
        raise ConfigError("appSelection must be a JSON object")

    selection = AppSelection(
        mode=str(selection_raw.get("mode", "all")).lower(),
        app_ids=_as_list(selection_raw.get("appIds", []), "appSelection.appIds"),
        app_names=_as_list(selection_raw.get("appNames", []), "appSelection.appNames"),
        app_file=str(selection_raw.get("appFile", "input/apps.txt")),
    )

    allowed_modes = {"all", "ids", "names", "file", "none"}
    if selection.mode not in allowed_modes:
        raise ConfigError(f"appSelection.mode must be one of: {', '.join(sorted(allowed_modes))}")

    config = ExportConfig(
        output_directory=str(data.get("outputDirectory", data.get("outputDir", "output"))),
        include_user_schemas=_as_bool(data.get("includeUserSchemas"), True),
        user_schema_ids=_as_list(data.get("userSchemaIds", ["default"]), "userSchemaIds"),
        include_group_schema=_as_bool(data.get("includeGroupSchema"), False),
        include_app_schemas=_as_bool(data.get("includeAppSchemas"), True),
        app_selection=selection,
        include_inactive_apps=_as_bool(data.get("includeInactiveApps"), False),
        skip_okta_system_apps=_as_bool(data.get("skipOktaSystemApps"), True),
        excluded_app_names=_as_list(data.get("excludedAppNames", DEFAULT_EXCLUDED_APP_NAMES), "excludedAppNames"),
        continue_on_app_schema_error=_as_bool(data.get("continueOnAppSchemaError"), True),
        write_individual_schema_files=_as_bool(data.get("writeIndividualSchemaFiles"), True),
        redact_sensitive_values=_as_bool(data.get("redactSensitiveValues"), True),
        timeout_seconds=int(data.get("timeoutSeconds", 30)),
        max_retries=int(data.get("maxRetries", 3)),
        okta_org_url=_normalize_org_url(os.getenv("OKTA_ORG_URL")),
        okta_api_token=os.getenv("OKTA_API_TOKEN"),
        raw=data,
    )

    if not config.include_user_schemas and not config.include_group_schema and not config.include_app_schemas:
        raise ConfigError("At least one schema category must be enabled")

    if config.include_user_schemas and not config.user_schema_ids:
        raise ConfigError("userSchemaIds must contain at least one schema ID when includeUserSchemas is true")

    if config.timeout_seconds <= 0:
        raise ConfigError("timeoutSeconds must be greater than zero")

    if config.max_retries < 0:
        raise ConfigError("maxRetries must be zero or greater")

    return config


def validate_runtime_config(config: ExportConfig, require_okta: bool = True) -> list[str]:
    warnings: list[str] = []
    if require_okta:
        if not config.okta_org_url:
            raise ConfigError("OKTA_ORG_URL is required in .env or environment")
        if not config.okta_api_token:
            raise ConfigError("OKTA_API_TOKEN is required in .env or environment")
        if not config.okta_org_url.startswith("https://"):
            warnings.append("OKTA_ORG_URL should use https://")
    if config.include_app_schemas and config.app_selection.mode == "ids" and not config.app_selection.app_ids:
        raise ConfigError("appSelection.appIds must not be empty when mode is ids")
    if config.include_app_schemas and config.app_selection.mode == "names" and not config.app_selection.app_names:
        raise ConfigError("appSelection.appNames must not be empty when mode is names")
    if config.include_app_schemas and config.app_selection.mode == "file":
        app_file = Path(config.app_selection.app_file)
        if not app_file.exists():
            raise ConfigError(f"appSelection.appFile not found: {app_file}")
    return warnings
