from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_EXCLUDED_APP_NAMES = [
    "saasure",
    "okta_enduser",
    "okta_browser_plugin",
    "okta_oin_submission_tester_app",
    "okta_iga_reviewer",
]

@dataclass
class AppSelection:
    mode: str = "all"
    app_ids: list[str] = field(default_factory=list)
    app_names: list[str] = field(default_factory=list)
    app_file: str = "input/apps.txt"

@dataclass
class ExportConfig:
    output_directory: str = "output"
    include_inactive_apps: bool = False
    include_app_schemas: bool = True
    include_profile_mappings: bool = True
    include_app_features: bool = True
    include_connector_details: bool = True
    skip_okta_system_apps: bool = True
    continue_on_app_schema_error: bool = True
    redact_sensitive_values: bool = True
    app_selection: AppSelection = field(default_factory=AppSelection)
    excluded_app_names: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDED_APP_NAMES))
    timeout_seconds: int = 30


def _bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ValueError(f"Expected boolean value, got {value!r}")


def load_config(path: str | Path) -> ExportConfig:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    selection_data = data.get("appSelection", {}) or {}
    selection = AppSelection(
        mode=str(selection_data.get("mode", "all")).lower(),
        app_ids=[str(x).strip() for x in selection_data.get("appIds", []) if str(x).strip()],
        app_names=[str(x).strip() for x in selection_data.get("appNames", []) if str(x).strip()],
        app_file=str(selection_data.get("appFile", "input/apps.txt")),
    )
    cfg = ExportConfig(
        output_directory=str(data.get("outputDirectory", "output")),
        include_inactive_apps=_bool(data.get("includeInactiveApps"), False),
        include_app_schemas=_bool(data.get("includeAppSchemas"), True),
        include_profile_mappings=_bool(data.get("includeProfileMappings"), True),
        include_app_features=_bool(data.get("includeAppFeatures"), True),
        include_connector_details=_bool(data.get("includeConnectorDetails"), True),
        skip_okta_system_apps=_bool(data.get("skipOktaSystemApps"), True),
        continue_on_app_schema_error=_bool(data.get("continueOnAppSchemaError"), True),
        redact_sensitive_values=_bool(data.get("redactSensitiveValues"), True),
        app_selection=selection,
        excluded_app_names=[str(x).strip() for x in data.get("excludedAppNames", DEFAULT_EXCLUDED_APP_NAMES) if str(x).strip()],
        timeout_seconds=int(data.get("timeoutSeconds", 30)),
    )
    validate_config(cfg)
    return cfg


def validate_config(cfg: ExportConfig) -> None:
    if cfg.timeout_seconds <= 0:
        raise ValueError("timeoutSeconds must be greater than zero")
    if cfg.app_selection.mode not in {"all", "ids", "names", "file"}:
        raise ValueError("appSelection.mode must be one of: all, ids, names, file")
    if cfg.app_selection.mode == "ids" and not cfg.app_selection.app_ids:
        raise ValueError("appSelection.mode ids requires appSelection.appIds")
    if cfg.app_selection.mode == "names" and not cfg.app_selection.app_names:
        raise ValueError("appSelection.mode names requires appSelection.appNames")
    if cfg.app_selection.mode == "file" and not cfg.app_selection.app_file:
        raise ValueError("appSelection.mode file requires appSelection.appFile")
