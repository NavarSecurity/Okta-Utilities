from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def normalize_org_url(url: str) -> str:
    value = (url or "").strip().rstrip("/")
    if not value:
        raise ValueError("Okta org URL is required. Set OKTA_ORG_URL or targetOrgUrl.")
    parsed = urlparse(value)
    if parsed.scheme not in {"https"}:
        raise ValueError("Okta org URL must start with https://")
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    if "-admin.okta" in host or "-admin.oktapreview" in host or host.endswith(".admin.okta.com"):
        raise ValueError("Use the normal Okta org URL, not the -admin Admin Console URL.")
    if path in {"/admin", "/api", "/api/v1"} or path.startswith("/admin/") or path.startswith("/api/"):
        raise ValueError("Use only the Okta org base URL, not /admin or /api/v1.")
    return value


@dataclass
class ExportOptions:
    rule_ids: list[str] = field(default_factory=list)
    rule_name_contains: str = ""
    statuses: list[str] = field(default_factory=lambda: ["ACTIVE", "INACTIVE"])
    include_inactive: bool = True
    expand_group_names: bool = True
    save_raw_responses: bool = False


@dataclass
class Settings:
    request_timeout_seconds: int = 30
    max_retries: int = 3
    page_limit: int = 200
    continue_on_error: bool = False


@dataclass
class AppConfig:
    target_org_url: str
    api_token: str
    output_dir: Path
    export: ExportOptions
    settings: Settings


def load_config(config_path: str | Path) -> AppConfig:
    _load_dotenv()
    path = Path(config_path)
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    org_url = os.getenv("OKTA_ORG_URL") or os.getenv("OKTA_TARGET_ORG_URL") or data.get("targetOrgUrl") or ""
    api_token = os.getenv("OKTA_API_TOKEN") or os.getenv("OKTA_TOKEN") or ""
    org_url = normalize_org_url(org_url)
    if not api_token:
        raise ValueError("OKTA_API_TOKEN is required in .env or environment variables.")

    export_data = data.get("export", {}) or {}
    settings_data = data.get("settings", {}) or {}

    statuses = [str(s).upper() for s in export_data.get("statuses", ["ACTIVE", "INACTIVE"])]
    if not export_data.get("includeInactive", True):
        statuses = [s for s in statuses if s != "INACTIVE"]

    page_limit = int(settings_data.get("pageLimit", 200))
    if page_limit < 1 or page_limit > 200:
        raise ValueError("settings.pageLimit must be between 1 and 200.")

    return AppConfig(
        target_org_url=org_url,
        api_token=api_token,
        output_dir=Path(data.get("outputDir", "output")),
        export=ExportOptions(
            rule_ids=[str(x) for x in export_data.get("ruleIds", [])],
            rule_name_contains=str(export_data.get("ruleNameContains", "") or ""),
            statuses=statuses,
            include_inactive=bool(export_data.get("includeInactive", True)),
            expand_group_names=bool(export_data.get("expandGroupNames", True)),
            save_raw_responses=bool(export_data.get("saveRawResponses", False)),
        ),
        settings=Settings(
            request_timeout_seconds=int(settings_data.get("requestTimeoutSeconds", 30)),
            max_retries=int(settings_data.get("maxRetries", 3)),
            page_limit=page_limit,
            continue_on_error=bool(settings_data.get("continueOnError", False)),
        ),
    )
