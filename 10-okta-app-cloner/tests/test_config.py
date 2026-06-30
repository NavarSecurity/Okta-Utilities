from pathlib import Path

import pytest

from okta_app_cloner.config import ConfigError, load_config


def test_load_sample_config(monkeypatch):
    monkeypatch.setenv("OKTA_TARGET_ORG_URL", "https://target.example.okta.com")
    monkeypatch.setenv("OKTA_TARGET_API_TOKEN", "fake-token")
    cfg = load_config(Path("samples/sample-cloner.config.json"))
    assert cfg.source_backup_dir == Path("samples/source-backup")
    assert cfg.selection["applications"]["labels"] == ["Customer Portal OIDC"]


def test_reject_ssws_prefix(monkeypatch):
    monkeypatch.setenv("OKTA_TARGET_ORG_URL", "https://target.example.okta.com")
    monkeypatch.setenv("OKTA_TARGET_API_TOKEN", "SSWS fake-token")
    with pytest.raises(ConfigError):
        load_config(Path("samples/sample-cloner.config.json"))
