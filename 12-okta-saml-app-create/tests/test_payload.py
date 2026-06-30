import pytest

from okta_saml_app_create.config import (
    AccessibilityConfig,
    SamlAppConfig,
    UserNameTemplateConfig,
    VisibilityConfig,
)
from okta_saml_app_create.payload import build_saml_app_payload


def test_build_saml_payload_minimum_valid():
    app = SamlAppConfig(
        label="Example SAML App",
        sso_acs_url="https://app.example.com/saml/acs",
        recipient="https://app.example.com/saml/acs",
        destination="https://app.example.com/saml/acs",
        audience="https://app.example.com/saml/metadata",
        attribute_statements=[{"type": "EXPRESSION", "name": "email", "namespace": "urn:oasis:names:tc:SAML:2.0:attrname-format:unspecified", "values": ["user.email"]}],
    )
    payload = build_saml_app_payload(app)
    assert "name" not in payload
    assert payload["signOnMode"] == "SAML_2_0"
    assert payload["label"] == "Example SAML App"
    assert payload["profile"]["label"] == "Example SAML App"
    assert payload["settings"]["signOn"]["ssoAcsUrl"] == "https://app.example.com/saml/acs"
    assert payload["settings"]["signOn"]["attributeStatements"][0]["values"] == ["user.email"]


def test_payload_uses_okta_saml_field_names():
    app = SamlAppConfig(
        label="App",
        sso_acs_url="https://example.com/acs",
        recipient="https://example.com/acs",
        destination="https://example.com/acs",
        audience="https://example.com/metadata",
    )
    payload = build_saml_app_payload(app)
    sign_on = payload["settings"]["signOn"]
    assert "ssoAcsUrl" in sign_on
    assert "subjectNameIdTemplate" in sign_on
    assert "subjectNameIdFormat" in sign_on
    assert "responseSigned" in sign_on
    assert "assertionSigned" in sign_on


def test_payload_does_not_emit_template_catalog_name():
    app = SamlAppConfig(
        label="Template Name Regression",
        sso_acs_url="https://example.com/acs",
        recipient="https://example.com/acs",
        destination="https://example.com/acs",
        audience="https://example.com/metadata",
    )
    payload = build_saml_app_payload(app)
    assert payload.get("name") is None
    assert payload["signOnMode"] == "SAML_2_0"
    assert payload["settings"]["signOn"]["audience"] == "https://example.com/metadata"


def test_payload_includes_visibility_accessibility_and_username_template_defaults():
    app = SamlAppConfig(
        label="Required Shape Regression",
        sso_acs_url="https://example.com/acs",
        recipient="https://example.com/acs",
        destination="https://example.com/acs",
        audience="https://example.com/metadata",
    )
    payload = build_saml_app_payload(app)
    assert payload["visibility"] == {
        "autoSubmitToolbar": False,
        "hide": {"iOS": False, "web": False},
    }
    assert payload["accessibility"] == {
        "selfService": False,
        "errorRedirectUrl": None,
        "loginRedirectUrl": None,
    }
    assert payload["credentials"]["userNameTemplate"] == {
        "template": "${source.login}",
        "type": "BUILT_IN",
    }


def test_payload_uses_custom_visibility_accessibility_and_username_template():
    app = SamlAppConfig(
        label="Custom Shape App",
        sso_acs_url="https://example.com/acs",
        recipient="https://example.com/acs",
        destination="https://example.com/acs",
        audience="https://example.com/metadata",
        visibility=VisibilityConfig(auto_submit_toolbar=True, hide_ios=True, hide_web=False),
        accessibility=AccessibilityConfig(
            self_service=True,
            error_redirect_url="https://example.com/error",
            login_redirect_url="https://example.com/login",
        ),
        user_name_template=UserNameTemplateConfig(template="${user.email}", type="CUSTOM"),
    )
    payload = build_saml_app_payload(app)
    assert payload["visibility"]["autoSubmitToolbar"] is True
    assert payload["visibility"]["hide"]["iOS"] is True
    assert payload["accessibility"]["selfService"] is True
    assert payload["accessibility"]["errorRedirectUrl"] == "https://example.com/error"
    assert payload["credentials"]["userNameTemplate"]["template"] == "${user.email}"
    assert payload["credentials"]["userNameTemplate"]["type"] == "CUSTOM"
