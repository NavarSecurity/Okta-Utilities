from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "outputDirectory": "output",
    "limit": 200,
    "includeMappingDetails": True,
    "filters": {"sourceId": "", "targetId": ""},
    "redactSensitiveValues": True,
    "timeoutSeconds": 30,
    "retry": {"maxAttempts": 3, "backoffSeconds": 1},
}


def load_dotenv(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        clean = line.strip()
        if not clean or clean.startswith("#") or "=" not in clean:
            continue
        key, value = clean.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(config_path: str | Path) -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        user_config = json.load(handle)
    config = deep_merge(DEFAULT_CONFIG, user_config)
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    limit = int(config.get("limit", 200))
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")

    filters = config.get("filters", {})
    if not isinstance(filters, dict):
        raise ValueError("filters must be an object")

    retry = config.get("retry", {})
    if int(retry.get("maxAttempts", 3)) < 1:
        raise ValueError("retry.maxAttempts must be at least 1")
    if float(retry.get("backoffSeconds", 1)) < 0:
        raise ValueError("retry.backoffSeconds must be zero or greater")


def get_okta_env() -> tuple[str, str]:
    org_url = os.environ.get("OKTA_ORG_URL", "").strip().rstrip("/")
    token = os.environ.get("OKTA_API_TOKEN", "").strip()
    if not org_url:
        raise ValueError("Missing OKTA_ORG_URL. Set it in .env or the environment.")
    if not token:
        raise ValueError("Missing OKTA_API_TOKEN. Set it in .env or the environment.")
    if org_url.endswith("/api/v1"):
        raise ValueError("OKTA_ORG_URL should not include /api/v1")
    return org_url, token
