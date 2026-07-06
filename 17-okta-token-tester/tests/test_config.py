import json
from pathlib import Path

import pytest

from okta_token_tester.config import load_config, normalize_issuer_url, normalize_org_url


def test_normalize_org_url_rejects_admin_url():
    with pytest.raises(ValueError):
        normalize_org_url("https://example-admin.okta.com")


def test_normalize_org_url_rejects_paths():
    with pytest.raises(ValueError):
        normalize_org_url("https://example.okta.com/oauth2/default")


def test_normalize_issuer_default():
    assert normalize_issuer_url("https://example.okta.com", "default") == "https://example.okta.com/oauth2/default"


def test_normalize_issuer_org():
    assert normalize_issuer_url("https://example.okta.com", "org") == "https://example.okta.com"


def test_load_config(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_ORG_URL", raising=False)
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"orgUrl": "https://example.okta.com", "authorizationServerId": "default"}), encoding="utf-8")
    cfg = load_config(cfg_path)
    assert cfg.org_url == "https://example.okta.com"
    assert cfg.issuer_url == "https://example.okta.com/oauth2/default"
