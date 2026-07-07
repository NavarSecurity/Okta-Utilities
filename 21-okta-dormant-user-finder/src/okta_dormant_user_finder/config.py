from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def normalize_org_url(url: str) -> str:
    value = (url or "").strip().rstrip("/")
    if not value:
        return value
    bad_fragments = ["/admin", "/api/v1", "/oauth2"]
    lowered = value.lower()
    if "-admin.okta.com" in lowered or "-admin.oktapreview.com" in lowered:
        raise ValueError("Use the normal Okta org URL, not the -admin Admin Console URL.")
    if any(fragment in lowered for fragment in bad_fragments):
        raise ValueError("Use only the Okta org base URL, for example https://example.okta.com.")
    return value


@dataclass
class SourceConfig:
    mode: str = "api"
    users_file: str = "input/users.csv"


@dataclass
class FiltersConfig:
    statuses: list[str] = field(default_factory=lambda: ["ACTIVE", "PROVISIONED", "STAGED", "SUSPENDED", "DEPROVISIONED"])
    exclude_user_ids: list[str] = field(default_factory=list)
    exclude_logins: list[str] = field(default_factory=list)
    exclude_login_domains: list[str] = field(default_factory=list)


@dataclass
class DormancyRules:
    stale_login_days: int = 90
    never_logged_in_after_days: int = 14
    inactive_statuses: list[str] = field(default_factory=lambda: ["STAGED", "SUSPENDED", "DEPROVISIONED"])
    flag_unassigned_to_apps: bool = True
    flag_no_group_membership: bool = False
    flag_password_not_changed_days: int | None = 365


@dataclass
class ApiOptions:
    fetch_app_links: bool = True
    fetch_groups: bool = False
    limit: int = 200
    request_timeout_seconds: int = 30
    max_retries: int = 3


@dataclass
class OutputConfig:
    include_raw_users: bool = False
    include_per_user_evidence: bool = True
    lifecycle_action: str = "deprovision"
    lifecycle_approved_default: str = ""
    lifecycle_reason_prefix: str = "Dormant user review candidate"


@dataclass
class AppConfig:
    org_url: str
    api_token: str = ""
    source: SourceConfig = field(default_factory=SourceConfig)
    filters: FiltersConfig = field(default_factory=FiltersConfig)
    dormancy_rules: DormancyRules = field(default_factory=DormancyRules)
    api_options: ApiOptions = field(default_factory=ApiOptions)
    output: OutputConfig = field(default_factory=OutputConfig)


def load_config(config_path: str | Path) -> AppConfig:
    _load_dotenv()
    path = Path(config_path)
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    org_url = os.getenv("OKTA_ORG_URL") or data.get("orgUrl") or ""
    org_url = normalize_org_url(org_url)
    api_token = os.getenv("OKTA_API_TOKEN") or data.get("apiToken") or ""

    source_data = data.get("source", {}) or {}
    filters_data = data.get("filters", {}) or {}
    rules_data = data.get("dormancyRules", {}) or {}
    api_data = data.get("apiOptions", {}) or {}
    output_data = data.get("output", {}) or {}

    source = SourceConfig(
        mode=str(source_data.get("mode", "api")).lower(),
        users_file=source_data.get("usersFile", "input/users.csv"),
    )
    if source.mode not in {"api", "file"}:
        raise ValueError("source.mode must be either 'api' or 'file'.")

    filters = FiltersConfig(
        statuses=[str(s).upper() for s in filters_data.get("statuses", FiltersConfig().statuses)],
        exclude_user_ids=[str(x) for x in filters_data.get("excludeUserIds", [])],
        exclude_logins=[str(x).lower() for x in filters_data.get("excludeLogins", [])],
        exclude_login_domains=[str(x).lower().lstrip("@") for x in filters_data.get("excludeLoginDomains", [])],
    )

    rules = DormancyRules(
        stale_login_days=int(rules_data.get("staleLoginDays", 90)),
        never_logged_in_after_days=int(rules_data.get("neverLoggedInAfterDays", 14)),
        inactive_statuses=[str(s).upper() for s in rules_data.get("inactiveStatuses", DormancyRules().inactive_statuses)],
        flag_unassigned_to_apps=bool(rules_data.get("flagUnassignedToApps", True)),
        flag_no_group_membership=bool(rules_data.get("flagNoGroupMembership", False)),
        flag_password_not_changed_days=(None if rules_data.get("flagPasswordNotChangedDays") is None else int(rules_data.get("flagPasswordNotChangedDays", 365))),
    )

    api_options = ApiOptions(
        fetch_app_links=bool(api_data.get("fetchAppLinks", True)),
        fetch_groups=bool(api_data.get("fetchGroups", False)),
        limit=int(api_data.get("limit", 200)),
        request_timeout_seconds=int(api_data.get("requestTimeoutSeconds", 30)),
        max_retries=int(api_data.get("maxRetries", 3)),
    )

    lifecycle_action = str(output_data.get("lifecycleAction", "deprovision")).strip().lower().replace("-", "_")
    if lifecycle_action == "deactivate":
        lifecycle_action = "deprovision"
    if lifecycle_action not in {"suspend", "deprovision", "delete", ""}:
        raise ValueError("output.lifecycleAction must be suspend, deprovision, delete, deactivate, or blank.")

    output = OutputConfig(
        include_raw_users=bool(output_data.get("includeRawUsers", False)),
        include_per_user_evidence=bool(output_data.get("includePerUserEvidence", True)),
        lifecycle_action=lifecycle_action,
        lifecycle_approved_default=str(output_data.get("lifecycleApprovedDefault", "")),
        lifecycle_reason_prefix=str(output_data.get("lifecycleReasonPrefix", "Dormant user review candidate")),
    )

    if source.mode == "api" and not api_token:
        raise ValueError("OKTA_API_TOKEN is required when source.mode is 'api'.")
    if source.mode == "api" and not org_url:
        raise ValueError("OKTA_ORG_URL or orgUrl is required when source.mode is 'api'.")

    return AppConfig(
        org_url=org_url,
        api_token=api_token,
        source=source,
        filters=filters,
        dormancy_rules=rules,
        api_options=api_options,
        output=output,
    )
