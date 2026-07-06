import json
from pathlib import Path

import pytest

from okta_user_exporter.config import ConfigError, load_config, normalize_org_url, is_sensitive_profile_key


def test_normalize_rejects_admin_url():
    with pytest.raises(ConfigError):
        normalize_org_url("https://example-admin.okta.com")


def test_normalize_rejects_api_path():
    with pytest.raises(ConfigError):
        normalize_org_url("https://example.okta.com/api/v1")


def test_normalize_accepts_org_url():
    assert normalize_org_url("https://example.okta.com/") == "https://example.okta.com"


def test_sensitive_profile_key_detection():
    assert is_sensitive_profile_key("clientSecret")
    assert is_sensitive_profile_key("api_token")
    assert not is_sensitive_profile_key("department")


def test_load_config_dry_run_does_not_require_token(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    monkeypatch.delenv("OKTA_ORG_URL", raising=False)
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"orgUrl": "https://example.okta.com"}), encoding="utf-8")
    loaded = load_config(cfg, require_token=False)
    assert loaded.org_url == "https://example.okta.com"
