from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


class ConfigError(ValueError):
    pass


def load_config(path: str | Path) -> dict[str, Any]:
    load_dotenv()
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Config file not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        if p.suffix.lower() in {".yaml", ".yml"}:
            data = yaml.safe_load(f) or {}
        else:
            data = json.load(f)

    org_url = os.getenv("OKTA_ORG_URL") or data.get("orgUrl") or ""
    token = os.getenv("OKTA_API_TOKEN") or data.get("apiToken") or ""
    org_url = normalize_org_url(org_url)
    if org_url:
        validate_org_url(org_url)
    data["orgUrl"] = org_url
    data["apiToken"] = token
    data.setdefault("mode", "api")
    data.setdefault("analysis", {})
    data.setdefault("settings", {})
    data.setdefault("outputDir", "output")
    validate_config(data)
    return data


def normalize_org_url(url: str) -> str:
    return (url or "").strip().rstrip("/")


def validate_org_url(url: str) -> None:
    lowered = url.lower()
    if "-admin.okta" in lowered or "-admin.oktapreview" in lowered:
        raise ConfigError("Use the normal Okta org URL, not the Admin Console -admin URL.")
    if lowered.endswith("/admin") or "/admin/" in lowered or lowered.endswith("/api/v1") or "/api/v1/" in lowered:
        raise ConfigError("Use only the Okta org base URL, not /admin or /api/v1.")
    if not lowered.startswith("https://"):
        raise ConfigError("Okta org URL must start with https://")


def validate_config(config: dict[str, Any]) -> None:
    mode = str(config.get("mode", "api")).lower()
    if mode != "api":
        raise ConfigError(
            "Utility 27 no longer supports file mode because CSV-only group data can create misleading empty/unused group findings. "
            "Use mode='api' so the utility can read current group data directly from Okta."
        )
    if not config.get("apiToken"):
        raise ConfigError("Okta API token is required for Utility 27 API mode.")
