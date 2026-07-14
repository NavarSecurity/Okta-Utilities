from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


DEFAULT_REDACT_KEYS = [
    "secret",
    "token",
    "password",
    "private",
    "authorization",
    "client_secret",
    "assertion",
]


@dataclass
class ExportFilters:
    types: list[str] = field(default_factory=list)
    statuses: list[str] = field(default_factory=list)


@dataclass
class RedactionConfig:
    replacement: str = "[REDACTED]"
    redact_key_names_containing: list[str] = field(default_factory=lambda: DEFAULT_REDACT_KEYS.copy())


@dataclass
class AppConfig:
    output_dir: str = "output"
    include_inactive: bool = True
    include_links: bool = False
    include_keys: bool = True
    split_by_type: bool = True
    redact_sensitive_values: bool = True
    filters: ExportFilters = field(default_factory=ExportFilters)
    redaction: RedactionConfig = field(default_factory=RedactionConfig)


@dataclass
class RuntimeConfig:
    app: AppConfig
    org_url: str | None
    api_token: str | None


def load_json_file(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def parse_app_config(raw: dict[str, Any]) -> AppConfig:
    filters_raw = raw.get("filters", {}) or {}
    redaction_raw = raw.get("redaction", {}) or {}

    filters = ExportFilters(
        types=[str(item).upper() for item in filters_raw.get("types", [])],
        statuses=[str(item).upper() for item in filters_raw.get("statuses", [])],
    )

    redaction = RedactionConfig(
        replacement=str(redaction_raw.get("replacement", "[REDACTED]")),
        redact_key_names_containing=[
            str(item).lower() for item in redaction_raw.get("redactKeyNamesContaining", DEFAULT_REDACT_KEYS)
        ],
    )

    return AppConfig(
        output_dir=str(raw.get("outputDir", raw.get("outputDirectory", "output"))),
        include_inactive=_as_bool(raw.get("includeInactive"), True),
        include_links=_as_bool(raw.get("includeLinks"), False),
        include_keys=_as_bool(raw.get("includeKeys"), True),
        split_by_type=_as_bool(raw.get("splitByType"), True),
        redact_sensitive_values=_as_bool(raw.get("redactSensitiveValues"), True),
        filters=filters,
        redaction=redaction,
    )


def load_runtime_config(config_path: str | Path) -> RuntimeConfig:
    load_dotenv()
    raw = load_json_file(config_path)
    app_config = parse_app_config(raw)
    org_url = os.getenv("OKTA_ORG_URL")
    api_token = os.getenv("OKTA_API_TOKEN")

    if org_url:
        org_url = org_url.rstrip("/")
        if org_url.endswith("/api/v1"):
            raise ValueError("OKTA_ORG_URL should not include /api/v1")

    return RuntimeConfig(app=app_config, org_url=org_url, api_token=api_token)


def validate_runtime_config(runtime: RuntimeConfig, require_okta: bool = True) -> list[str]:
    errors: list[str] = []

    if require_okta:
        if not runtime.org_url:
            errors.append("OKTA_ORG_URL is required for this run.")
        if not runtime.api_token:
            errors.append("OKTA_API_TOKEN is required for this run.")
        if runtime.org_url and not runtime.org_url.startswith("https://"):
            errors.append("OKTA_ORG_URL should start with https://")

    if not runtime.app.output_dir:
        errors.append("outputDir is required.")

    return errors
