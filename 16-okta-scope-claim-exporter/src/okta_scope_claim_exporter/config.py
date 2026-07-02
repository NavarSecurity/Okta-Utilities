from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None


@dataclass
class ExportSettings:
    include_inactive_authorization_servers: bool = True
    include_scopes: bool = True
    include_claims: bool = True
    include_raw_responses: bool = False
    continue_on_error: bool = True
    request_timeout_seconds: int = 30
    max_retries: int = 3


@dataclass
class ExportFilters:
    authorization_server_ids: list[str] = field(default_factory=list)
    authorization_server_names: list[str] = field(default_factory=list)
    exclude_authorization_server_ids: list[str] = field(default_factory=list)
    exclude_authorization_server_names: list[str] = field(default_factory=list)


@dataclass
class ExportConfig:
    source_org_url: str
    output_dir: Path
    settings: ExportSettings
    filters: ExportFilters
    api_token: str | None = None


def normalize_org_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if not url:
        raise ValueError("Missing Okta org URL")

    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError(f"Invalid Okta org URL: {url}")

    host = parsed.netloc.lower()
    path = parsed.path.strip("/")

    if "-admin.okta" in host or "-admin.oktapreview" in host or "-admin.okta-emea" in host:
        raise ValueError("Use the normal Okta org URL, not the Admin Console -admin URL")

    if path and path not in {""}:
        raise ValueError("Use the Okta org base URL only. Do not include /admin, /api/v1, or /oauth2 paths")

    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Expected a list of strings")
    result: list[str] = []
    for item in value:
        if item is None:
            continue
        if not isinstance(item, str):
            raise ValueError("Expected a list of strings")
        if item.strip():
            result.append(item.strip())
    return result


def load_config(config_path: str | Path) -> ExportConfig:
    if load_dotenv:
        load_dotenv()

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    env_url = os.getenv("OKTA_SOURCE_ORG_URL") or os.getenv("OKTA_ORG_URL")
    source_org_url = normalize_org_url(env_url or raw.get("sourceOrgUrl", ""))

    output_dir = Path(raw.get("outputDir") or "output")

    settings_raw = raw.get("settings") or {}
    settings = ExportSettings(
        include_inactive_authorization_servers=bool(settings_raw.get("includeInactiveAuthorizationServers", True)),
        include_scopes=bool(settings_raw.get("includeScopes", True)),
        include_claims=bool(settings_raw.get("includeClaims", True)),
        include_raw_responses=bool(settings_raw.get("includeRawResponses", False)),
        continue_on_error=bool(settings_raw.get("continueOnError", True)),
        request_timeout_seconds=int(settings_raw.get("requestTimeoutSeconds", 30)),
        max_retries=int(settings_raw.get("maxRetries", 3)),
    )

    if settings.request_timeout_seconds <= 0:
        raise ValueError("requestTimeoutSeconds must be greater than 0")
    if settings.max_retries < 0:
        raise ValueError("maxRetries must be 0 or greater")

    filters_raw = raw.get("filters") or {}
    filters = ExportFilters(
        authorization_server_ids=_as_string_list(filters_raw.get("authorizationServerIds", [])),
        authorization_server_names=_as_string_list(filters_raw.get("authorizationServerNames", [])),
        exclude_authorization_server_ids=_as_string_list(filters_raw.get("excludeAuthorizationServerIds", [])),
        exclude_authorization_server_names=_as_string_list(filters_raw.get("excludeAuthorizationServerNames", [])),
    )

    api_token = os.getenv("OKTA_API_TOKEN") or os.getenv("OKTA_SOURCE_API_TOKEN")

    return ExportConfig(
        source_org_url=source_org_url,
        output_dir=output_dir,
        settings=settings,
        filters=filters,
        api_token=api_token,
    )
