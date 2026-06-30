import json
from pathlib import Path

import pytest

from okta_oidc_app_create.config import load_config, validate_runtime


def test_load_config(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_TARGET_API_TOKEN", raising=False)
    p = tmp_path / "config.json"
    p.write_text(json.dumps({
        "targetOrgUrl": "https://example.okta.com",
        "applications": [{
            "label": "App",
            "applicationType": "web",
            "grantTypes": ["authorization_code"],
            "responseTypes": ["code"]
        }]
    }))
    cfg = load_config(p)
    assert cfg.target_org_url == "https://example.okta.com"
    assert cfg.applications[0].label == "App"


def test_invalid_app_type(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({
        "targetOrgUrl": "https://example.okta.com",
        "applications": [{
            "label": "App",
            "applicationType": "bad",
            "grantTypes": ["authorization_code"],
            "responseTypes": ["code"]
        }]
    }))
    with pytest.raises(ValueError):
        load_config(p)


def test_apply_requires_token(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_API_TOKEN", raising=False)
    p = tmp_path / "config.json"
    p.write_text(json.dumps({
        "targetOrgUrl": "https://example.okta.com",
        "applications": [{
            "label": "App",
            "applicationType": "web",
            "grantTypes": ["authorization_code"],
            "responseTypes": ["code"]
        }]
    }))
    cfg = load_config(p)
    errors = validate_runtime(cfg, apply=True)
    assert any("OKTA_TARGET_API_TOKEN" in e for e in errors)
