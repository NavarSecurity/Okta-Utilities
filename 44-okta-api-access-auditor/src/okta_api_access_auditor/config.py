from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


DEFAULT_HIGH_RISK_SCOPES = [
    "okta.apiTokens.manage",
    "okta.apps.manage",
    "okta.authorizationServers.manage",
    "okta.clients.manage",
    "okta.groups.manage",
    "okta.policies.manage",
    "okta.roles.manage",
    "okta.users.manage",
]

DEFAULT_HIGH_RISK_ROLES = [
    "SUPER_ADMIN",
    "ORG_ADMIN",
    "API_ACCESS_MANAGEMENT_ADMIN",
    "APP_ADMIN",
    "USER_ADMIN",
    "GROUP_ADMIN",
    "CUSTOM",
]


@dataclass
class AppSelection:
    mode: str = "service"
    app_ids: list[str] = field(default_factory=list)
    app_names: list[str] = field(default_factory=list)
    app_file: str = "input/apps.txt"


@dataclass
class RiskRules:
    stale_api_token_days: int = 90
    old_api_token_days: int = 365
    stale_app_days: int = 180
    high_risk_scopes: list[str] = field(default_factory=lambda: DEFAULT_HIGH_RISK_SCOPES.copy())
    high_risk_roles: list[str] = field(default_factory=lambda: DEFAULT_HIGH_RISK_ROLES.copy())
    flag_client_with_scopes_but_no_roles: bool = True
    flag_client_with_roles_but_no_scopes: bool = True
    flag_broad_network_api_tokens: bool = True


@dataclass
class Config:
    output_directory: str = "output"
    include_api_tokens: bool = True
    include_oauth_apps: bool = True
    include_app_grants: bool = True
    include_client_role_assignments: bool = True
    include_inactive_apps: bool = False
    continue_on_request_error: bool = True
    redact_sensitive_values: bool = True
    timeout_seconds: int = 30
    app_selection: AppSelection = field(default_factory=AppSelection)
    risk_rules: RiskRules = field(default_factory=RiskRules)


class ConfigError(ValueError):
    pass


def _camel(data: dict[str, Any], key: str, default: Any = None) -> Any:
    return data.get(key, default)


def load_config(path: str | Path) -> Config:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    selection = raw.get("appSelection", {}) or {}
    risk = raw.get("riskRules", {}) or {}

    return Config(
        output_directory=_camel(raw, "outputDirectory", "output"),
        include_api_tokens=bool(_camel(raw, "includeApiTokens", True)),
        include_oauth_apps=bool(_camel(raw, "includeOAuthApps", True)),
        include_app_grants=bool(_camel(raw, "includeAppGrants", True)),
        include_client_role_assignments=bool(_camel(raw, "includeClientRoleAssignments", True)),
        include_inactive_apps=bool(_camel(raw, "includeInactiveApps", False)),
        continue_on_request_error=bool(_camel(raw, "continueOnRequestError", True)),
        redact_sensitive_values=bool(_camel(raw, "redactSensitiveValues", True)),
        timeout_seconds=int(_camel(raw, "timeoutSeconds", 30)),
        app_selection=AppSelection(
            mode=str(selection.get("mode", "service")),
            app_ids=list(selection.get("appIds", []) or []),
            app_names=list(selection.get("appNames", []) or []),
            app_file=str(selection.get("appFile", "input/apps.txt")),
        ),
        risk_rules=RiskRules(
            stale_api_token_days=int(risk.get("staleApiTokenDays", 90)),
            old_api_token_days=int(risk.get("oldApiTokenDays", 365)),
            stale_app_days=int(risk.get("staleAppDays", 180)),
            high_risk_scopes=list(risk.get("highRiskScopes", DEFAULT_HIGH_RISK_SCOPES) or []),
            high_risk_roles=list(risk.get("highRiskRoles", DEFAULT_HIGH_RISK_ROLES) or []),
            flag_client_with_scopes_but_no_roles=bool(risk.get("flagClientWithScopesButNoRoles", True)),
            flag_client_with_roles_but_no_scopes=bool(risk.get("flagClientWithRolesButNoScopes", True)),
            flag_broad_network_api_tokens=bool(risk.get("flagBroadNetworkApiTokens", True)),
        ),
    )


def load_env() -> tuple[str, str]:
    load_dotenv()
    org_url = (os.getenv("OKTA_ORG_URL") or "").strip().rstrip("/")
    api_token = (os.getenv("OKTA_API_TOKEN") or "").strip()
    if not org_url:
        raise ConfigError("OKTA_ORG_URL is required in .env or environment variables")
    if not api_token:
        raise ConfigError("OKTA_API_TOKEN is required in .env or environment variables")
    if org_url.endswith("/api/v1"):
        raise ConfigError("OKTA_ORG_URL should be the base org URL, not a /api/v1 URL")
    return org_url, api_token


def read_lines_if_exists(path: str | Path) -> list[str]:
    p = Path(path)
    if not p.exists():
        return []
    lines: list[str] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            lines.append(value)
    return lines
