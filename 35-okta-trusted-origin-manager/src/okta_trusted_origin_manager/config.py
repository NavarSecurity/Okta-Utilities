from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


class ConfigError(ValueError):
    """Raised when configuration is invalid."""


@dataclass
class RuntimeConfig:
    operation: str
    output_directory: Path
    raw: dict[str, Any]
    okta_org_url: str | None = None
    okta_api_token: str | None = None
    timeout_seconds: int = 30
    max_retries: int = 3


def load_json(path: str | Path) -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.exists():
        raise ConfigError(f"Config file not found: {candidate}")
    if not candidate.is_file():
        raise ConfigError(f"Config path is not a file: {candidate}")
    try:
        return json.loads(candidate.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in config file {candidate}: {exc}") from exc


def _clean_org_url(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().rstrip("/")
    if cleaned.endswith("/api/v1"):
        cleaned = cleaned[: -len("/api/v1")]
    return cleaned


def get_output_directory(raw: dict[str, Any]) -> Path:
    return Path(raw.get("outputDirectory") or raw.get("outputDir") or "output")


def load_config(config_path: str | Path, operation_override: str | None = None) -> RuntimeConfig:
    load_dotenv()
    raw = load_json(config_path)
    operation = (operation_override or raw.get("operation") or "export").strip().lower()
    if operation not in {"export", "compare", "validate", "import"}:
        raise ConfigError("operation must be one of: export, compare, validate, import")

    timeout = int(raw.get("timeoutSeconds", 30))
    max_retries = int(raw.get("maxRetries", 3))
    if timeout <= 0:
        raise ConfigError("timeoutSeconds must be greater than zero")
    if max_retries < 0:
        raise ConfigError("maxRetries cannot be negative")

    return RuntimeConfig(
        operation=operation,
        output_directory=get_output_directory(raw),
        raw=raw,
        okta_org_url=_clean_org_url(os.getenv("OKTA_ORG_URL") or raw.get("oktaOrgUrl")),
        okta_api_token=os.getenv("OKTA_API_TOKEN") or raw.get("oktaApiToken"),
        timeout_seconds=timeout,
        max_retries=max_retries,
    )


def require_okta_settings(config: RuntimeConfig) -> None:
    if not config.okta_org_url:
        raise ConfigError("OKTA_ORG_URL is required for this operation")
    if not config.okta_api_token:
        raise ConfigError("OKTA_API_TOKEN is required for this operation")
    if not config.okta_org_url.startswith("https://"):
        raise ConfigError("OKTA_ORG_URL should start with https:// and should not include /api/v1")
