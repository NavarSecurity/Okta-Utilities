from __future__ import annotations

from typing import Any

from .config import SamlAppConfig, ConfigError

_VALID_SIGNATURE_ALGORITHMS = {"RSA_SHA1", "RSA_SHA256", "RSA_SHA384", "RSA_SHA512"}
_VALID_DIGEST_ALGORITHMS = {"SHA1", "SHA256", "SHA384", "SHA512"}
_VALID_NAME_ID_FORMAT_PREFIX = "urn:oasis:names:tc:SAML:"


def validate_saml_app_config(app: SamlAppConfig) -> list[str]:
    warnings: list[str] = []
    url_fields = {
        "ssoAcsUrl": app.sso_acs_url,
        "recipient": app.recipient,
        "destination": app.destination,
    }
    for name, value in url_fields.items():
        if not value.startswith("https://"):
            raise ConfigError(f"app.{name} must be an HTTPS URL")
    if not app.audience:
        raise ConfigError("app.audience is required")
    if not app.subject_name_id_format.startswith(_VALID_NAME_ID_FORMAT_PREFIX):
        warnings.append("subjectNameIdFormat does not look like a standard SAML NameID format URI")
    if app.signature_algorithm not in _VALID_SIGNATURE_ALGORITHMS:
        raise ConfigError(f"Unsupported signatureAlgorithm: {app.signature_algorithm}")
    if app.digest_algorithm not in _VALID_DIGEST_ALGORITHMS:
        raise ConfigError(f"Unsupported digestAlgorithm: {app.digest_algorithm}")
    if not app.attribute_statements:
        warnings.append("No attributeStatements configured")
    return warnings


def build_saml_app_payload(app: SamlAppConfig) -> dict[str, Any]:
    validate_saml_app_config(app)

    sign_on = {
        "defaultRelayState": app.default_relay_state,
        "ssoAcsUrl": app.sso_acs_url,
        "recipient": app.recipient,
        "destination": app.destination,
        "audience": app.audience,
        "subjectNameIdTemplate": app.subject_name_id_template,
        "subjectNameIdFormat": app.subject_name_id_format,
        "responseSigned": app.response_signed,
        "assertionSigned": app.assertion_signed,
        "signatureAlgorithm": app.signature_algorithm,
        "digestAlgorithm": app.digest_algorithm,
        "honorForceAuthn": app.honor_force_authn,
        "authnContextClassRef": app.authn_context_class_ref,
    }

    if app.attribute_statements:
        sign_on["attributeStatements"] = app.attribute_statements

    # Do not include a catalog/template app `name` such as `template_saml_2_0`.
    # Some Okta orgs reject that value with `Resource not found: template_saml_2_0 (App)`.
    # The payload intentionally relies on the explicit SAML sign-on mode and settings.
    return {
        "label": app.label,
        "signOnMode": "SAML_2_0",
        "profile": {
            "label": app.label,
        },
        "accessibility": {
            "selfService": app.accessibility.self_service,
            "errorRedirectUrl": app.accessibility.error_redirect_url,
            "loginRedirectUrl": app.accessibility.login_redirect_url,
        },
        "visibility": {
            "autoSubmitToolbar": app.visibility.auto_submit_toolbar,
            "hide": {
                "iOS": app.visibility.hide_ios,
                "web": app.visibility.hide_web,
            },
        },
        "credentials": {
            "userNameTemplate": {
                "template": app.user_name_template.template,
                "type": app.user_name_template.type,
            },
        },
        "settings": {
            "app": {},
            "signOn": sign_on,
        },
    }
