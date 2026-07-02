from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

from .util import normalize_org_url, read_json


@dataclass
class BuildSettings:
    skip_existing: bool = True
    continue_on_error: bool = False
    request_timeout_seconds: int = 30
    max_retries: int = 3


@dataclass
class BuilderConfig:
    target_org_url: str
    api_token: str
    settings: BuildSettings
    authorization_servers: List[Dict[str, Any]]
    source_path: Path


def load_config(config_path: str | Path, require_api_token: bool = True) -> BuilderConfig:
    load_dotenv()
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    raw = read_json(path)
    target_org_url = os.getenv("OKTA_TARGET_ORG_URL") or raw.get("targetOrgUrl")
    api_token = os.getenv("OKTA_API_TOKEN") or raw.get("apiToken")

    if not api_token and require_api_token:
        raise ValueError("OKTA_API_TOKEN is required in .env, environment, or config when using --apply.")
    api_token = api_token or ""

    settings_raw = raw.get("settings", {}) or {}
    settings = BuildSettings(
        skip_existing=bool(settings_raw.get("skipExisting", True)),
        continue_on_error=bool(settings_raw.get("continueOnError", False)),
        request_timeout_seconds=int(settings_raw.get("requestTimeoutSeconds", 30)),
        max_retries=int(settings_raw.get("maxRetries", 3)),
    )

    servers = raw.get("authorizationServers") or []
    if not isinstance(servers, list) or not servers:
        raise ValueError("authorizationServers must be a non-empty list.")

    return BuilderConfig(
        target_org_url=normalize_org_url(target_org_url),
        api_token=str(api_token),
        settings=settings,
        authorization_servers=servers,
        source_path=path,
    )
