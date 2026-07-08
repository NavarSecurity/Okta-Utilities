import json
from pathlib import Path

import pytest

from okta_group_rule_exporter.config import load_config, normalize_org_url


def test_normalize_rejects_admin_url():
    with pytest.raises(ValueError):
        normalize_org_url("https://example-admin.okta.com")


def test_normalize_rejects_api_path():
    with pytest.raises(ValueError):
        normalize_org_url("https://example.okta.com/api/v1")


def test_load_config_env_priority(tmp_path, monkeypatch):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"targetOrgUrl": "https://wrong.okta.com"}))
    monkeypatch.setenv("OKTA_ORG_URL", "https://right.okta.com")
    monkeypatch.setenv("OKTA_API_TOKEN", "abc")
    loaded = load_config(config)
    assert loaded.target_org_url == "https://right.okta.com"
