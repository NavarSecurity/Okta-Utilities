import json
from pathlib import Path

import pytest

from okta_saml_app_create.config import load_config, ConfigError


def test_load_config_requires_real_org(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_TARGET_API_TOKEN", raising=False)
    data = {
        "targetOrgUrl": "https://your-okta-org.okta.com",
        "app": {
            "label": "App",
            "ssoAcsUrl": "https://example.com/acs",
            "recipient": "https://example.com/acs",
            "destination": "https://example.com/acs",
            "audience": "https://example.com/metadata",
        },
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_env_overrides_org_url(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OKTA_TARGET_ORG_URL", "https://example.okta.com")
    monkeypatch.setenv("OKTA_TARGET_API_TOKEN", "abc")
    data = {
        "targetOrgUrl": "https://placeholder.okta.com",
        "app": {
            "label": "App",
            "ssoAcsUrl": "https://example.com/acs",
            "recipient": "https://example.com/acs",
            "destination": "https://example.com/acs",
            "audience": "https://example.com/metadata",
        },
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    cfg = load_config(path)
    assert cfg.target_org_url == "https://example.okta.com"
    assert cfg.target_api_token == "abc"


def test_token_must_not_include_ssws(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OKTA_TARGET_ORG_URL", "https://example.okta.com")
    monkeypatch.setenv("OKTA_TARGET_API_TOKEN", "SSWS abc")
    data = {
        "app": {
            "label": "App",
            "ssoAcsUrl": "https://example.com/acs",
            "recipient": "https://example.com/acs",
            "destination": "https://example.com/acs",
            "audience": "https://example.com/metadata",
        },
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_rejects_admin_domain(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OKTA_TARGET_ORG_URL", "https://example-admin.okta.com")
    monkeypatch.setenv("OKTA_TARGET_API_TOKEN", "abc")
    data = {
        "app": {
            "label": "App",
            "ssoAcsUrl": "https://example.com/acs",
            "recipient": "https://example.com/acs",
            "destination": "https://example.com/acs",
            "audience": "https://example.com/metadata",
        },
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_load_config_parses_visibility_accessibility_and_username_template(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OKTA_TARGET_ORG_URL", "https://example.okta.com")
    monkeypatch.delenv("OKTA_TARGET_API_TOKEN", raising=False)
    data = {
        "app": {
            "label": "App",
            "ssoAcsUrl": "https://example.com/acs",
            "recipient": "https://example.com/acs",
            "destination": "https://example.com/acs",
            "audience": "https://example.com/metadata",
            "visibility": {
                "autoSubmitToolbar": True,
                "hide": {"iOS": True, "web": False},
            },
            "accessibility": {
                "selfService": True,
                "errorRedirectUrl": "https://example.com/error",
                "loginRedirectUrl": "https://example.com/login",
            },
            "userNameTemplate": {
                "template": "${user.email}",
                "type": "CUSTOM",
            },
        },
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    cfg = load_config(path)
    assert cfg.app.visibility.auto_submit_toolbar is True
    assert cfg.app.visibility.hide_ios is True
    assert cfg.app.visibility.hide_web is False
    assert cfg.app.accessibility.self_service is True
    assert cfg.app.accessibility.error_redirect_url == "https://example.com/error"
    assert cfg.app.user_name_template.template == "${user.email}"
    assert cfg.app.user_name_template.type == "CUSTOM"


def test_accessibility_redirect_urls_must_be_https(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OKTA_TARGET_ORG_URL", "https://example.okta.com")
    monkeypatch.delenv("OKTA_TARGET_API_TOKEN", raising=False)
    data = {
        "app": {
            "label": "App",
            "ssoAcsUrl": "https://example.com/acs",
            "recipient": "https://example.com/acs",
            "destination": "https://example.com/acs",
            "audience": "https://example.com/metadata",
            "accessibility": {"loginRedirectUrl": "http://example.com/login"},
        },
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)
