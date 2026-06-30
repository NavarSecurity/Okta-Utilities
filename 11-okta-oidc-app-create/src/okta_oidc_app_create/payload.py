from __future__ import annotations

from typing import Any

from .config import OidcAppConfig


def _strip_empty(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = {k: _strip_empty(v) for k, v in value.items()}
        return {k: v for k, v in cleaned.items() if v is not None and v != [] and v != {}}
    if isinstance(value, list):
        return [_strip_empty(v) for v in value]
    return value


def build_oidc_app_payload(app: OidcAppConfig) -> dict[str, Any]:
    """Build an Okta /api/v1/apps OIDC application payload.

    Important: Okta's OAuth client credential properties belong under
    credentials.oauthClient. That includes token_endpoint_auth_method and
    pkce_required. Settings such as application_type, grant_types, response_types,
    and redirect URIs belong under settings.oauthClient.
    """
    settings_oauth_client: dict[str, Any] = {
        "application_type": app.application_type,
        "grant_types": app.grant_types,
        "response_types": app.response_types,
        "redirect_uris": app.redirect_uris,
        "post_logout_redirect_uris": app.post_logout_redirect_uris,
        # Okta's Apps API create payload supports initiate_login_uri, but not
        # login_uri in settings.oauthClient. Do not emit login_uri; use
        # initiateLoginUri in config for app-tile initiated flows.
        "initiate_login_uri": app.initiate_login_uri,
        "consent_method": app.consent_method,
        "issuer_mode": app.issuer_mode,
    }

    credentials_oauth_client: dict[str, Any] = {}
    if app.token_endpoint_auth_method:
        credentials_oauth_client["token_endpoint_auth_method"] = app.token_endpoint_auth_method
    # Omit pkce_required when false because false is the default for
    # confidential web clients and older/classic orgs can reject unnecessary
    # credential flags. Include it only when true.
    if app.pkce_required is True:
        credentials_oauth_client["pkce_required"] = True

    payload = {
        "name": "oidc_client",
        "label": app.label,
        "signOnMode": "OPENID_CONNECT",
        "credentials": {"oauthClient": credentials_oauth_client},
        "profile": {"label": app.label},
        "settings": {"oauthClient": settings_oauth_client},
    }
    return _strip_empty(payload)


def safe_payload_preview(payload: dict[str, Any]) -> dict[str, Any]:
    # OIDC create payloads should not contain secrets, but keep this defensive.
    sensitive_keys = {"client_secret", "clientSecret", "secret", "password", "privateKey", "private_key"}

    def walk(value: Any) -> Any:
        if isinstance(value, dict):
            out = {}
            for k, v in value.items():
                if k in sensitive_keys:
                    out[k] = "[REDACTED]"
                else:
                    out[k] = walk(v)
            return out
        if isinstance(value, list):
            return [walk(v) for v in value]
        return value

    return walk(payload)
