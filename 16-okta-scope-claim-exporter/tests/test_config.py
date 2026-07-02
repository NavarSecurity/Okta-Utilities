import json

import pytest

from okta_scope_claim_exporter.config import load_config, normalize_org_url


def test_normalize_org_url_accepts_base_url():
    assert normalize_org_url("https://example.okta.com/") == "https://example.okta.com"


def test_normalize_org_url_rejects_admin_url():
    with pytest.raises(ValueError, match="Admin Console"):
        normalize_org_url("https://example-admin.okta.com")


def test_normalize_org_url_rejects_path():
    with pytest.raises(ValueError, match="base URL"):
        normalize_org_url("https://example.okta.com/api/v1")


def test_load_config_env_url_wins(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"sourceOrgUrl": "https://wrong.okta.com"}), encoding="utf-8")
    monkeypatch.setenv("OKTA_SOURCE_ORG_URL", "https://right.okta.com")
    cfg = load_config(config_path)
    assert cfg.source_org_url == "https://right.okta.com"


def test_load_config_filters(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_SOURCE_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_ORG_URL", raising=False)
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "sourceOrgUrl": "https://example.okta.com",
                "filters": {
                    "authorizationServerIds": ["aus1"],
                    "authorizationServerNames": ["Server One"],
                    "excludeAuthorizationServerIds": ["aus2"],
                    "excludeAuthorizationServerNames": ["Server Two"],
                },
            }
        ),
        encoding="utf-8",
    )
    cfg = load_config(config_path)
    assert cfg.filters.authorization_server_ids == ["aus1"]
    assert cfg.filters.authorization_server_names == ["Server One"]
    assert cfg.filters.exclude_authorization_server_ids == ["aus2"]
    assert cfg.filters.exclude_authorization_server_names == ["Server Two"]
