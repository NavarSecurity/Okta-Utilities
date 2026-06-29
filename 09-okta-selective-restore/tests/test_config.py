import json
from pathlib import Path

import pytest

from okta_selective_restore.config import ConfigError, load_config


def test_load_config_uses_env_for_target(tmp_path: Path, monkeypatch):
    backup = tmp_path / "backup"
    backup.mkdir()
    cfg = tmp_path / "restore.config.json"
    cfg.write_text(json.dumps({"sourceBackupDir": str(backup), "targetOrgUrl": "https://placeholder.okta.com"}), encoding="utf-8")
    monkeypatch.setenv("OKTA_TARGET_ORG_URL", "https://real.okta.com")
    monkeypatch.setenv("OKTA_TARGET_API_TOKEN", "abc")
    loaded = load_config(cfg)
    assert loaded.target_org_url == "https://real.okta.com"
    assert loaded.target_api_token == "abc"


def test_load_config_rejects_ssws_prefix(tmp_path: Path, monkeypatch):
    backup = tmp_path / "backup"
    backup.mkdir()
    cfg = tmp_path / "restore.config.json"
    cfg.write_text(json.dumps({"sourceBackupDir": str(backup), "targetOrgUrl": "https://target.okta.com"}), encoding="utf-8")
    monkeypatch.setenv("OKTA_TARGET_API_TOKEN", "SSWS abc")
    with pytest.raises(ConfigError):
        load_config(cfg)
