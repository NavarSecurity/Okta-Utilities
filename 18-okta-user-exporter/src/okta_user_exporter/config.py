from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


class ConfigError(ValueError):
    pass


SENSITIVE_PROFILE_KEYS = {
    "password",
    "passcode",
    "secret",
    "clientsecret",
    "client_secret",
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "apikey",
    "api_key",
    "ssn",
    "socialsecuritynumber",
}


@dataclass
class Settings:
    request_timeout_seconds: int = 30
    max_retries: int = 3
    page_limit: int = 200
    max_users: Optional[int] = None
    continue_on_error: bool = True
    save_raw_responses: bool = False
    redact_sensitive_profile_fields: bool = True


@dataclass
class Filters:
    statuses: List[str] = field(default_factory=list)
    query: str = ""
    search: str = ""
    filter: str = ""
    user_ids: List[str] = field(default_factory=list)
    login_contains: str = ""
    profile_fields: List[str] = field(default_factory=lambda: ["login", "email", "firstName", "lastName"])
    include_profile_all: bool = False


@dataclass
class Include:
    groups: bool = True
    app_links: bool = True


@dataclass
class OutputNames:
    users_csv: str = "users.csv"
    users_json: str = "users.json"
    user_groups_csv: str = "user_groups.csv"
    user_app_links_csv: str = "user_app_links.csv"
    summary_csv: str = "user_export_summary.csv"
    result_json: str = "user_export_result.json"
    report_markdown: str = "user_export_report.md"


@dataclass
class ExportConfig:
    org_url: str
    api_token: str = ""
    settings: Settings = field(default_factory=Settings)
    filters: Filters = field(default_factory=Filters)
    include: Include = field(default_factory=Include)
    output: OutputNames = field(default_factory=OutputNames)
    config_path: Optional[Path] = None


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def normalize_org_url(url: str) -> str:
    if not url:
        raise ConfigError("Okta org URL is required. Set orgUrl in config or OKTA_ORG_URL in .env.")
    normalized = url.strip().rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"https"} or not parsed.netloc:
        raise ConfigError("Okta org URL must be a full https URL, such as https://your-org.okta.com.")
    host = parsed.netloc.lower()
    path = parsed.path.lower().rstrip("/")
    if "-admin.okta" in host or "-admin.oktapreview" in host or path.startswith("/admin"):
        raise ConfigError("Use the normal Okta org URL, not the Admin Console URL. Example: https://your-org.okta.com")
    if path.startswith("/api/") or "/oauth2" in path:
        raise ConfigError("Use only the Okta org base URL. Do not include /api/v1 or /oauth2 paths.")
    return f"{parsed.scheme}://{parsed.netloc}"


def load_config(config_path: str | Path, require_token: bool = False) -> ExportConfig:
    _load_dotenv()
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    data: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))

    org_url = os.getenv("OKTA_ORG_URL") or os.getenv("OKTA_TARGET_ORG_URL") or data.get("orgUrl", "")
    api_token = os.getenv("OKTA_API_TOKEN", "")

    normalized_org_url = normalize_org_url(org_url)
    if require_token and not api_token:
        raise ConfigError("OKTA_API_TOKEN is required for --export mode.")

    settings_data = data.get("settings", {}) or {}
    filters_data = data.get("filters", {}) or {}
    include_data = data.get("include", {}) or {}
    output_data = data.get("output", {}) or {}

    settings = Settings(
        request_timeout_seconds=int(settings_data.get("requestTimeoutSeconds", 30)),
        max_retries=int(settings_data.get("maxRetries", 3)),
        page_limit=int(settings_data.get("pageLimit", 200)),
        max_users=settings_data.get("maxUsers"),
        continue_on_error=bool(settings_data.get("continueOnError", True)),
        save_raw_responses=bool(settings_data.get("saveRawResponses", False)),
        redact_sensitive_profile_fields=bool(settings_data.get("redactSensitiveProfileFields", True)),
    )
    if settings.max_users is not None:
        settings.max_users = int(settings.max_users)
    if settings.page_limit < 1 or settings.page_limit > 200:
        raise ConfigError("settings.pageLimit must be between 1 and 200.")

    filters = Filters(
        statuses=[str(s).upper() for s in filters_data.get("statuses", [])],
        query=str(filters_data.get("query", "") or ""),
        search=str(filters_data.get("search", "") or ""),
        filter=str(filters_data.get("filter", "") or ""),
        user_ids=[str(u) for u in filters_data.get("userIds", [])],
        login_contains=str(filters_data.get("loginContains", "") or "").lower(),
        profile_fields=[str(f) for f in filters_data.get("profileFields", ["login", "email", "firstName", "lastName"])],
        include_profile_all=bool(filters_data.get("includeProfileAll", False)),
    )

    include = Include(
        groups=bool(include_data.get("groups", True)),
        app_links=bool(include_data.get("appLinks", True)),
    )

    output = OutputNames(
        users_csv=output_data.get("usersCsv", "users.csv"),
        users_json=output_data.get("usersJson", "users.json"),
        user_groups_csv=output_data.get("userGroupsCsv", "user_groups.csv"),
        user_app_links_csv=output_data.get("userAppLinksCsv", "user_app_links.csv"),
        summary_csv=output_data.get("summaryCsv", "user_export_summary.csv"),
        result_json=output_data.get("resultJson", "user_export_result.json"),
        report_markdown=output_data.get("reportMarkdown", "user_export_report.md"),
    )

    return ExportConfig(
        org_url=normalized_org_url,
        api_token=api_token,
        settings=settings,
        filters=filters,
        include=include,
        output=output,
        config_path=path,
    )


def is_sensitive_profile_key(key: str) -> bool:
    normalized = key.replace("-", "_").replace(" ", "").lower()
    return any(s in normalized for s in SENSITIVE_PROFILE_KEYS)
