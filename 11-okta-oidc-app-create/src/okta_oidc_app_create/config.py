from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import os

from dotenv import load_dotenv


SUPPORTED_APP_TYPES = {"web", "browser", "native", "service"}
SUPPORTED_TOKEN_ENDPOINT_AUTH_METHODS = {
    "client_secret_basic",
    "client_secret_post",
    "client_secret_jwt",
    "private_key_jwt",
    "none",
}


@dataclass
class AssignmentConfig:
    groups: list[str] = field(default_factory=list)
    users: list[str] = field(default_factory=list)


@dataclass
class OidcAppConfig:
    label: str
    application_type: str
    grant_types: list[str]
    response_types: list[str]
    redirect_uris: list[str] = field(default_factory=list)
    post_logout_redirect_uris: list[str] = field(default_factory=list)
    login_uri: str | None = None
    initiate_login_uri: str | None = None
    pkce_required: bool | None = None
    token_endpoint_auth_method: str | None = None
    consent_method: str | None = None
    issuer_mode: str | None = None
    assignments: AssignmentConfig = field(default_factory=AssignmentConfig)


@dataclass
class RuntimeConfig:
    target_org_url: str | None
    api_token: str | None
    output_dir: Path
    create_assignments: bool
    skip_existing: bool
    fail_fast: bool
    page_limit: int
    timeout_seconds: int
    max_retries: int
    retry_base_seconds: float
    applications: list[OidcAppConfig]


def _as_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} must be a list of strings")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON config file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Config root must be a JSON object")
    return data


def load_config(config_path: str | Path) -> RuntimeConfig:
    load_dotenv()
    path = Path(config_path)
    data = _load_json(path)

    target_org_url = os.getenv("OKTA_TARGET_ORG_URL") or data.get("targetOrgUrl")
    api_token = os.getenv("OKTA_TARGET_API_TOKEN")

    apps_data = data.get("applications", [])
    if not isinstance(apps_data, list) or not apps_data:
        raise ValueError("applications must be a non-empty list")

    apps: list[OidcAppConfig] = []
    for i, raw in enumerate(apps_data):
        if not isinstance(raw, dict):
            raise ValueError(f"applications[{i}] must be an object")
        label = raw.get("label")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"applications[{i}].label is required")
        application_type = raw.get("applicationType", "web")
        if application_type not in SUPPORTED_APP_TYPES:
            raise ValueError(f"applications[{i}].applicationType must be one of {sorted(SUPPORTED_APP_TYPES)}")
        grant_types = _as_list(raw.get("grantTypes"), f"applications[{i}].grantTypes")
        response_types = _as_list(raw.get("responseTypes"), f"applications[{i}].responseTypes")
        if not grant_types:
            raise ValueError(f"applications[{i}].grantTypes must not be empty")
        if not response_types:
            raise ValueError(f"applications[{i}].responseTypes must not be empty")
        token_method = raw.get("tokenEndpointAuthMethod")
        if token_method is not None and token_method not in SUPPORTED_TOKEN_ENDPOINT_AUTH_METHODS:
            raise ValueError(
                f"applications[{i}].tokenEndpointAuthMethod must be one of "
                f"{sorted(SUPPORTED_TOKEN_ENDPOINT_AUTH_METHODS)}"
            )
        assignments_data = raw.get("assignments") or {}
        if not isinstance(assignments_data, dict):
            raise ValueError(f"applications[{i}].assignments must be an object")
        apps.append(
            OidcAppConfig(
                label=label.strip(),
                application_type=application_type,
                grant_types=grant_types,
                response_types=response_types,
                redirect_uris=_as_list(raw.get("redirectUris"), f"applications[{i}].redirectUris"),
                post_logout_redirect_uris=_as_list(
                    raw.get("postLogoutRedirectUris"), f"applications[{i}].postLogoutRedirectUris"
                ),
                login_uri=raw.get("loginUri"),
                initiate_login_uri=raw.get("initiateLoginUri"),
                pkce_required=raw.get("pkceRequired"),
                token_endpoint_auth_method=token_method,
                consent_method=raw.get("consentMethod"),
                issuer_mode=raw.get("issuerMode"),
                assignments=AssignmentConfig(
                    groups=_as_list(assignments_data.get("groups"), f"applications[{i}].assignments.groups"),
                    users=_as_list(assignments_data.get("users"), f"applications[{i}].assignments.users"),
                ),
            )
        )

    return RuntimeConfig(
        target_org_url=target_org_url.rstrip("/") if isinstance(target_org_url, str) else None,
        api_token=api_token,
        output_dir=Path(data.get("outputDir", "output")),
        create_assignments=bool(data.get("createAssignments", False)),
        skip_existing=bool(data.get("skipExisting", True)),
        fail_fast=bool(data.get("failFast", False)),
        page_limit=int(data.get("pageLimit", 200)),
        timeout_seconds=int(data.get("timeoutSeconds", 30)),
        max_retries=int(data.get("maxRetries", 4)),
        retry_base_seconds=float(data.get("retryBaseSeconds", 1.0)),
        applications=apps,
    )



def _validate_app_shape(app: OidcAppConfig, index: int) -> list[str]:
    errors: list[str] = []
    grants = set(app.grant_types)
    responses = set(app.response_types)

    if {"token", "id_token"} & responses and "implicit" not in grants:
        errors.append(
            f"applications[{index}] responseTypes token/id_token require grantTypes to include implicit"
        )

    if app.application_type in {"browser", "native"}:
        if app.token_endpoint_auth_method not in {None, "none"}:
            errors.append(
                f"applications[{index}] public clients ({app.application_type}) should use tokenEndpointAuthMethod 'none'"
            )
        if "authorization_code" in grants and app.pkce_required is False:
            errors.append(
                f"applications[{index}] public clients using authorization_code should set pkceRequired true"
            )

    if app.application_type == "web" and app.token_endpoint_auth_method == "none":
        errors.append(
            f"applications[{index}] web apps should generally use a client authentication method such as client_secret_basic or client_secret_post"
        )

    # loginUri is intentionally ignored by the payload builder, rather than
    # rejected, so existing configs remain backward-compatible. Use
    # initiateLoginUri for app-tile initiated OIDC flows.

    return errors

def validate_runtime(config: RuntimeConfig, apply: bool) -> list[str]:
    errors: list[str] = []
    if not config.target_org_url:
        errors.append("targetOrgUrl or OKTA_TARGET_ORG_URL is required")
    elif not config.target_org_url.startswith("https://"):
        errors.append("targetOrgUrl must be an HTTPS URL")
    if apply and not config.api_token:
        errors.append("OKTA_TARGET_API_TOKEN is required in apply mode")
    for i, app in enumerate(config.applications):
        errors.extend(_validate_app_shape(app, i))
    return errors
