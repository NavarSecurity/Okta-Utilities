from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    okta_org_url: str | None
    okta_api_token: str | None
    input_file: Path
    output_directory: Path
    check_existing: bool
    on_existing: str
    continue_on_error: bool
    redact_sensitive_values: bool
    timeout_seconds: int
    allow_app_schema_updates: bool
    allow_user_schema_updates: bool
    raw: dict[str, Any]


def load_json(path: str | Path) -> dict[str, Any]:
    resolved = Path(path)
    if not resolved.exists():
        raise ConfigError(f"Config file not found: {resolved}")
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {resolved}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("Config JSON must be an object.")
    return data


def load_settings(config_path: str | Path) -> Settings:
    load_dotenv()
    raw = load_json(config_path)

    input_file = Path(raw.get("inputFile", "input/profile_attributes.create.json"))
    output_directory = Path(raw.get("outputDirectory", raw.get("outputDir", "output")))

    on_existing = str(raw.get("onExisting", "skip")).lower().strip()
    if on_existing not in {"skip", "update", "fail"}:
        raise ConfigError("onExisting must be one of: skip, update, fail.")

    timeout_seconds = int(raw.get("timeoutSeconds", 30))
    if timeout_seconds < 1:
        raise ConfigError("timeoutSeconds must be greater than zero.")

    return Settings(
        okta_org_url=os.getenv("OKTA_ORG_URL"),
        okta_api_token=os.getenv("OKTA_API_TOKEN"),
        input_file=input_file,
        output_directory=output_directory,
        check_existing=bool(raw.get("checkExisting", True)),
        on_existing=on_existing,
        continue_on_error=bool(raw.get("continueOnError", True)),
        redact_sensitive_values=bool(raw.get("redactSensitiveValues", True)),
        timeout_seconds=timeout_seconds,
        allow_app_schema_updates=bool(raw.get("allowAppSchemaUpdates", True)),
        allow_user_schema_updates=bool(raw.get("allowUserSchemaUpdates", True)),
        raw=raw,
    )


def load_input_file(path: str | Path) -> dict[str, Any]:
    resolved = Path(path)
    if not resolved.exists():
        raise ConfigError(f"Input file not found: {resolved}")
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {resolved}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("Input JSON must be an object.")
    if "attributes" not in data or not isinstance(data["attributes"], list):
        raise ConfigError("Input file must include an attributes array.")
    return data
