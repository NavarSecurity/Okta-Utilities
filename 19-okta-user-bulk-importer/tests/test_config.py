import json
import os
from pathlib import Path

import pytest

from okta_user_bulk_importer.config import load_config


def write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_load_config_uses_env(monkeypatch, tmp_path):
    monkeypatch.setenv("OKTA_TARGET_ORG_URL", "https://example.okta.com")
    monkeypatch.setenv("OKTA_API_TOKEN", "token")
    path = write_config(tmp_path, {"targetOrgUrl": "https://ignored.okta.com"})
    cfg = load_config(path)
    assert cfg.targetOrgUrl == "https://example.okta.com"
    assert cfg.apiToken == "token"


def test_rejects_admin_url(monkeypatch, tmp_path):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.setenv("OKTA_API_TOKEN", "token")
    path = write_config(tmp_path, {"targetOrgUrl": "https://example-admin.okta.com"})
    with pytest.raises(ValueError, match="Admin Console"):
        load_config(path)


def test_rejects_unsafe_duplicate_config(monkeypatch, tmp_path):
    monkeypatch.setenv("OKTA_TARGET_ORG_URL", "https://example.okta.com")
    monkeypatch.setenv("OKTA_API_TOKEN", "token")
    path = write_config(tmp_path, {"settings": {"skipExisting": False, "updateExisting": False}})
    with pytest.raises(ValueError, match="Unsafe config"):
        load_config(path)
