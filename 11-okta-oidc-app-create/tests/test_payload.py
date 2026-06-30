from okta_oidc_app_create.config import OidcAppConfig
from okta_oidc_app_create.payload import build_oidc_app_payload


def test_build_oidc_web_app_payload_omits_login_uri_and_false_pkce():
    app = OidcAppConfig(
        label="Customer Portal OIDC",
        application_type="web",
        grant_types=["authorization_code"],
        response_types=["code"],
        redirect_uris=["https://app.example.com/callback"],
        post_logout_redirect_uris=["https://app.example.com/logout"],
        login_uri="https://app.example.com/login",
        initiate_login_uri="https://app.example.com/login",
        pkce_required=False,
        token_endpoint_auth_method="client_secret_basic",
        consent_method="REQUIRED",
    )
    payload = build_oidc_app_payload(app)
    assert payload["name"] == "oidc_client"
    assert payload["label"] == "Customer Portal OIDC"
    assert payload["profile"]["label"] == "Customer Portal OIDC"
    assert payload["signOnMode"] == "OPENID_CONNECT"
    oauth = payload["settings"]["oauthClient"]
    assert oauth["application_type"] == "web"
    assert oauth["initiate_login_uri"] == "https://app.example.com/login"
    assert "login_uri" not in oauth
    assert "pkce_required" not in oauth
    assert payload["credentials"]["oauthClient"]["token_endpoint_auth_method"] == "client_secret_basic"
    assert "pkce_required" not in payload["credentials"]["oauthClient"]


def test_build_oidc_browser_app_payload_places_true_pkce_under_credentials():
    app = OidcAppConfig(
        label="SPA OIDC",
        application_type="browser",
        grant_types=["authorization_code"],
        response_types=["code"],
        redirect_uris=["https://spa.example.com/callback"],
        pkce_required=True,
        token_endpoint_auth_method="none",
    )
    payload = build_oidc_app_payload(app)
    assert payload["credentials"]["oauthClient"]["token_endpoint_auth_method"] == "none"
    assert payload["credentials"]["oauthClient"]["pkce_required"] is True
    assert "pkce_required" not in payload["settings"]["oauthClient"]


def test_empty_optional_fields_are_removed():
    app = OidcAppConfig(
        label="SPA",
        application_type="browser",
        grant_types=["authorization_code"],
        response_types=["code"],
        token_endpoint_auth_method="none",
    )
    payload = build_oidc_app_payload(app)
    oauth = payload["settings"]["oauthClient"]
    assert "redirect_uris" not in oauth
    assert "login_uri" not in oauth
    assert "initiate_login_uri" not in oauth
    assert "pkce_required" not in payload["credentials"]["oauthClient"]
