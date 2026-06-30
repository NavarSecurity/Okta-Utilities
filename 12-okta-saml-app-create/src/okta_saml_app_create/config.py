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
class Assignments:
    group_ids: list[str] = field(default_factory=list)
    user_ids: list[str] = field(default_factory=list)


@dataclass
class VisibilityConfig:
    auto_submit_toolbar: bool = False
    hide_ios: bool = False
    hide_web: bool = False


@dataclass
class AccessibilityConfig:
    self_service: bool = False
    error_redirect_url: str | None = None
    login_redirect_url: str | None = None


@dataclass
class UserNameTemplateConfig:
    template: str = "${source.login}"
    type: str = "BUILT_IN"


@dataclass
class SamlAppConfig:
    label: str
    sso_acs_url: str
    recipient: str
    destination: str
    audience: str
    default_relay_state: str = ""
    subject_name_id_template: str = "${user.email}"
    subject_name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    response_signed: bool = True
    assertion_signed: bool = True
    signature_algorithm: str = "RSA_SHA256"
    digest_algorithm: str = "SHA256"
    honor_force_authn: bool = False
    authn_context_class_ref: str = "urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport"
    attribute_statements: list[dict[str, Any]] = field(default_factory=list)
    visibility: VisibilityConfig = field(default_factory=VisibilityConfig)
    accessibility: AccessibilityConfig = field(default_factory=AccessibilityConfig)
    user_name_template: UserNameTemplateConfig = field(default_factory=UserNameTemplateConfig)
    assignments: Assignments = field(default_factory=Assignments)


@dataclass
class RuntimeConfig:
    target_org_url: str
    target_api_token: str | None
    output_dir: Path
    skip_existing: bool
    fail_fast: bool
    page_limit: int
    timeout_seconds: int
    max_retries: int
    retry_base_seconds: float
    app: SamlAppConfig


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
    value = value.strip().rstrip("/")
    if not value.startswith("https://"):
        raise ConfigError("targetOrgUrl must be an HTTPS URL")
    if value.endswith("/admin") or "/admin/" in value:
        raise ConfigError("targetOrgUrl must be the Okta org base URL, not an /admin URL")
    if "-admin.okta.com" in value or "-admin.oktapreview.com" in value:
        raise ConfigError("targetOrgUrl must use the normal Okta org base URL, not the -admin domain")
    if "/api/v1" in value or "/oauth2" in value:
        raise ConfigError("targetOrgUrl must not include /api/v1 or /oauth2")
    return value


def _required_str(source: dict[str, Any], key: str) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"app.{key} is required and must be a non-empty string")
    return value.strip()


def _optional_str(source: dict[str, Any], key: str, default: str = "") -> str:
    value = source.get(key, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ConfigError(f"app.{key} must be a string")
    return value.strip()


def _optional_bool(source: dict[str, Any], key: str, default: bool, label: str | None = None) -> bool:
    value = source.get(key, default)
    if not isinstance(value, bool):
        raise ConfigError(f"app.{label or key} must be true or false")
    return value


def _list_of_strings(value: Any, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ConfigError(f"{label} must be a list of non-empty strings")
    return [item.strip() for item in value]


def _parse_attribute_statements(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ConfigError("app.attributeStatements must be a list")
    parsed: list[dict[str, Any]] = []
    for idx, item in enumerate(value):
        if not isinstance(item, dict):
            raise ConfigError(f"app.attributeStatements[{idx}] must be an object")
        name = item.get("name")
        values = item.get("values")
        if not isinstance(name, str) or not name.strip():
            raise ConfigError(f"app.attributeStatements[{idx}].name is required")
        if not isinstance(values, list) or not values or not all(isinstance(v, str) and v.strip() for v in values):
            raise ConfigError(f"app.attributeStatements[{idx}].values must be a non-empty list of strings")
        stmt = {
            "type": item.get("type", "EXPRESSION"),
            "name": name.strip(),
            "namespace": item.get("namespace", "urn:oasis:names:tc:SAML:2.0:attrname-format:unspecified"),
            "values": [v.strip() for v in values],
        }
        if stmt["type"] not in {"EXPRESSION", "GROUP"}:
            raise ConfigError(f"app.attributeStatements[{idx}].type must be EXPRESSION or GROUP")
        parsed.append(stmt)
    return parsed




def _parse_visibility(value: Any) -> VisibilityConfig:
    if value is None:
        return VisibilityConfig()
    if not isinstance(value, dict):
        raise ConfigError("app.visibility must be an object")
    hide = value.get("hide", {})
    if hide is None:
        hide = {}
    if not isinstance(hide, dict):
        raise ConfigError("app.visibility.hide must be an object")
    return VisibilityConfig(
        auto_submit_toolbar=_optional_bool(value, "autoSubmitToolbar", False, "visibility.autoSubmitToolbar"),
        hide_ios=_optional_bool(hide, "iOS", False, "visibility.hide.iOS"),
        hide_web=_optional_bool(hide, "web", False, "visibility.hide.web"),
    )


def _parse_accessibility(value: Any) -> AccessibilityConfig:
    if value is None:
        return AccessibilityConfig()
    if not isinstance(value, dict):
        raise ConfigError("app.accessibility must be an object")

    def nullable_url(key: str) -> str | None:
        raw = value.get(key)
        if raw is None or raw == "":
            return None
        if not isinstance(raw, str):
            raise ConfigError(f"app.accessibility.{key} must be a string or null")
        raw = raw.strip()
        if raw and not raw.startswith("https://"):
            raise ConfigError(f"app.accessibility.{key} must be an HTTPS URL when set")
        return raw or None

    return AccessibilityConfig(
        self_service=_optional_bool(value, "selfService", False, "accessibility.selfService"),
        error_redirect_url=nullable_url("errorRedirectUrl"),
        login_redirect_url=nullable_url("loginRedirectUrl"),
    )


def _parse_user_name_template(value: Any) -> UserNameTemplateConfig:
    if value is None:
        return UserNameTemplateConfig()
    if not isinstance(value, dict):
        raise ConfigError("app.userNameTemplate must be an object")
    template = _optional_str(value, "template", "${source.login}")
    type_value = _optional_str(value, "type", "BUILT_IN")
    if type_value not in {"BUILT_IN", "CUSTOM"}:
        raise ConfigError("app.userNameTemplate.type must be BUILT_IN or CUSTOM")
    if not template:
        raise ConfigError("app.userNameTemplate.template must not be blank")
    return UserNameTemplateConfig(template=template, type=type_value)


def _parse_app(data: dict[str, Any]) -> SamlAppConfig:
    raw = data.get("app")
    if not isinstance(raw, dict):
        raise ConfigError("Config must include an app object")

    assignments_raw = raw.get("assignments", {})
    if assignments_raw is None:
        assignments_raw = {}
    if not isinstance(assignments_raw, dict):
        raise ConfigError("app.assignments must be an object")
    assignments = Assignments(
        group_ids=_list_of_strings(assignments_raw.get("groupIds"), "app.assignments.groupIds"),
        user_ids=_list_of_strings(assignments_raw.get("userIds"), "app.assignments.userIds"),
    )

    return SamlAppConfig(
        label=_required_str(raw, "label"),
        sso_acs_url=_required_str(raw, "ssoAcsUrl"),
        recipient=_required_str(raw, "recipient"),
        destination=_required_str(raw, "destination"),
        audience=_required_str(raw, "audience"),
        default_relay_state=_optional_str(raw, "defaultRelayState", ""),
        subject_name_id_template=_optional_str(raw, "subjectNameIdTemplate", "${user.email}"),
        subject_name_id_format=_optional_str(raw, "subjectNameIdFormat", "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"),
        response_signed=_optional_bool(raw, "responseSigned", True),
        assertion_signed=_optional_bool(raw, "assertionSigned", True),
        signature_algorithm=_optional_str(raw, "signatureAlgorithm", "RSA_SHA256"),
        digest_algorithm=_optional_str(raw, "digestAlgorithm", "SHA256"),
        honor_force_authn=_optional_bool(raw, "honorForceAuthn", False),
        authn_context_class_ref=_optional_str(raw, "authnContextClassRef", "urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport"),
        attribute_statements=_parse_attribute_statements(raw.get("attributeStatements", [])),
        visibility=_parse_visibility(raw.get("visibility")),
        accessibility=_parse_accessibility(raw.get("accessibility")),
        user_name_template=_parse_user_name_template(raw.get("userNameTemplate")),
        assignments=assignments,
    )


def load_config(path: Path) -> RuntimeConfig:
    load_dotenv()
    data = _read_json(path)
    target_org_url = _clean_org_url(os.getenv("OKTA_TARGET_ORG_URL") or data.get("targetOrgUrl"))
    if not target_org_url or "your-okta-org" in target_org_url:
        raise ConfigError("A real targetOrgUrl is required in .env or config")

    token = os.getenv("OKTA_TARGET_API_TOKEN")
    if token:
        token = token.strip()
        if token.upper().startswith("SSWS "):
            raise ConfigError("OKTA_TARGET_API_TOKEN must not include the SSWS prefix")

    return RuntimeConfig(
        target_org_url=target_org_url,
        target_api_token=token,
        output_dir=Path(data.get("outputDir", "output")),
        skip_existing=bool(data.get("skipExisting", True)),
        fail_fast=bool(data.get("failFast", False)),
        page_limit=int(data.get("pageLimit", 200)),
        timeout_seconds=int(data.get("timeoutSeconds", 30)),
        max_retries=int(data.get("maxRetries", 4)),
        retry_base_seconds=float(data.get("retryBaseSeconds", 1.0)),
        app=_parse_app(data),
    )
