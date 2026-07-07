import json
import os
from pathlib import Path

import pytest

from okta_dormant_user_finder.config import load_config, normalize_org_url


def test_rejects_admin_url():
    with pytest.raises(ValueError):
        normalize_org_url("https://example-admin.okta.com")


def test_load_file_mode_config_without_token(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    monkeypatch.delenv("OKTA_ORG_URL", raising=False)
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"orgUrl": "https://example.okta.com", "source": {"mode": "file", "usersFile": "input/users.csv"}}))
    config = load_config(path)
    assert config.source.mode == "file"
    assert config.org_url == "https://example.okta.com"


def test_api_mode_requires_token(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    monkeypatch.delenv("OKTA_ORG_URL", raising=False)
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"orgUrl": "https://example.okta.com", "source": {"mode": "api"}}))
    with pytest.raises(ValueError):
        load_config(path)
