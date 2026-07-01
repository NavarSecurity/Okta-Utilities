from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import os

from dotenv import load_dotenv


class ConfigError(ValueError):
    pass


@dataclass
class AppSelection:
    mode: str = "all"
    app_ids: list[str] = field(default_factory=list)
    app_labels: list[str] = field(default_factory=list)
    statuses: list[str] = field(default_factory=lambda: ["ACTIVE"])
    sign_on_modes: list[str] = field(default_factory=list)
    exclude_app_ids: list[str] = field(default_factory=list)
    exclude_app_labels: list[str] = field(default_factory=list)


@dataclass
class ExportOptions:
    include_users: bool = True
    include_groups: bool = True
    include_user_profile: bool = False
    include_group_profile: bool = False
    include_raw_assignments: bool = False
    max_apps: int | None = None
    fail_fast: bool = False


@dataclass
class HttpConfig:
    page_limit: int = 200
    timeout_seconds: int = 30
    max_retries: int = 4
    retry_base_seconds: float = 1.0


@dataclass
class RuntimeConfig:
    target_org_url: str
    api_token: str | None
    output_dir: Path
    app_selection: AppSelection
    export_options: ExportOptions
    http: HttpConfig


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Config file is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("Config file must contain a JSON object")
    return data


def _clean_org_url(value: str | None) -> str:
    if not value:
        return ""
    cleaned = str(value).strip().rstrip("/")
    if not cleaned:
        return ""
    if not cleaned.startswith("https://"):
        raise ConfigError("targetOrgUrl must be an HTTPS URL")
    if cleaned.endswith("/admin") or "/admin/" in cleaned:
        raise ConfigError("targetOrgUrl must be the Okta org base URL, not an /admin URL")
    if "-admin.okta.com" in cleaned or "-admin.oktapreview.com" in cleaned:
        raise ConfigError("targetOrgUrl must use the normal Okta org base URL, not the -admin domain")
    forbidden_fragments = ["/api/v1", "/oauth2", "/app/", "/login/"]
    if any(fragment in cleaned for fragment in forbidden_fragments):
        raise ConfigError("targetOrgUrl must be the Okta org base URL only, for example https://example.okta.com")
    return cleaned


def _string_list(value: Any, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ConfigError(f"{name} must be a list")
    output: list[str] = []
    for item in value:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            output.append(text)
    return output


def _bool(value: Any, default: bool, name: str) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ConfigError(f"{name} must be true or false")


def _optional_int(value: Any, name: str) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ConfigError(f"{name} must be a positive integer or null")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be a positive integer or null") from exc
    if parsed <= 0:
        raise ConfigError(f"{name} must be greater than zero when set")
    return parsed


def _positive_int(value: Any, default: int, name: str) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        raise ConfigError(f"{name} must be a positive integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be a positive integer") from exc
    if parsed <= 0:
        raise ConfigError(f"{name} must be greater than zero")
    return parsed


def _positive_float(value: Any, default: float, name: str) -> float:
    if value is None:
        return default
    if isinstance(value, bool):
        raise ConfigError(f"{name} must be a positive number")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be a positive number") from exc
    if parsed <= 0:
        raise ConfigError(f"{name} must be greater than zero")
    return parsed


def _load_app_selection(data: dict[str, Any]) -> AppSelection:
    raw = data.get("appSelection", {})
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ConfigError("appSelection must be an object")
    mode = str(raw.get("mode", "all")).strip().lower()
    if mode not in {"all", "ids", "labels"}:
        raise ConfigError("appSelection.mode must be one of: all, ids, labels")
    selection = AppSelection(
        mode=mode,
        app_ids=_string_list(raw.get("appIds", []), "appSelection.appIds"),
        app_labels=_string_list(raw.get("appLabels", []), "appSelection.appLabels"),
        statuses=[status.upper() for status in _string_list(raw.get("statuses", ["ACTIVE"]), "appSelection.statuses")],
        sign_on_modes=[mode.upper() for mode in _string_list(raw.get("signOnModes", []), "appSelection.signOnModes")],
        exclude_app_ids=_string_list(raw.get("excludeAppIds", []), "appSelection.excludeAppIds"),
        exclude_app_labels=_string_list(raw.get("excludeAppLabels", []), "appSelection.excludeAppLabels"),
    )
    if selection.mode == "ids" and not selection.app_ids:
        raise ConfigError("appSelection.appIds is required when mode is ids")
    if selection.mode == "labels" and not selection.app_labels:
        raise ConfigError("appSelection.appLabels is required when mode is labels")
    return selection


def _load_export_options(data: dict[str, Any]) -> ExportOptions:
    raw = data.get("exportOptions", {})
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ConfigError("exportOptions must be an object")
    return ExportOptions(
        include_users=_bool(raw.get("includeUsers"), True, "exportOptions.includeUsers"),
        include_groups=_bool(raw.get("includeGroups"), True, "exportOptions.includeGroups"),
        include_user_profile=_bool(raw.get("includeUserProfile"), False, "exportOptions.includeUserProfile"),
        include_group_profile=_bool(raw.get("includeGroupProfile"), False, "exportOptions.includeGroupProfile"),
        include_raw_assignments=_bool(raw.get("includeRawAssignments"), False, "exportOptions.includeRawAssignments"),
        max_apps=_optional_int(raw.get("maxApps"), "exportOptions.maxApps"),
        fail_fast=_bool(raw.get("failFast"), False, "exportOptions.failFast"),
    )


def _load_http(data: dict[str, Any]) -> HttpConfig:
    raw = data.get("http", {})
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ConfigError("http must be an object")
    page_limit = _positive_int(raw.get("pageLimit"), 200, "http.pageLimit")
    if page_limit > 200:
        raise ConfigError("http.pageLimit cannot be greater than 200")
    return HttpConfig(
        page_limit=page_limit,
        timeout_seconds=_positive_int(raw.get("timeoutSeconds"), 30, "http.timeoutSeconds"),
        max_retries=_positive_int(raw.get("maxRetries"), 4, "http.maxRetries"),
        retry_base_seconds=_positive_float(raw.get("retryBaseSeconds"), 1.0, "http.retryBaseSeconds"),
    )


def load_config(path: Path) -> RuntimeConfig:
    load_dotenv()
    data = _read_json(path)

    target_org_url = _clean_org_url(
        os.getenv("OKTA_ORG_URL")
        or os.getenv("OKTA_TARGET_ORG_URL")
        or data.get("targetOrgUrl")
    )
    if not target_org_url:
        raise ConfigError("targetOrgUrl is required in config or OKTA_ORG_URL is required in .env")

    output_dir = Path(os.getenv("OKTA_OUTPUT_DIR") or data.get("outputDir") or "output")
    api_token = (os.getenv("OKTA_API_TOKEN") or os.getenv("OKTA_TARGET_API_TOKEN") or data.get("apiToken") or "").strip() or None

    return RuntimeConfig(
        target_org_url=target_org_url,
        api_token=api_token,
        output_dir=output_dir,
        app_selection=_load_app_selection(data),
        export_options=_load_export_options(data),
        http=_load_http(data),
    )
