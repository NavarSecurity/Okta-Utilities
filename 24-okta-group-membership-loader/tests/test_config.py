import json
from pathlib import Path

import pytest

from okta_group_membership_loader.config import ConfigError, load_config


def test_rejects_admin_url(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"targetOrgUrl": "https://example-admin.okta.com", "membershipFile": "input/a.csv"}))
    with pytest.raises(ConfigError):
        load_config(p)


def test_loads_membership_file(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"targetOrgUrl": "https://example.okta.com", "membershipFile": "input/a.csv"}))
    cfg = load_config(p)
    assert cfg.membership_file == "input/a.csv"
    assert cfg.default_action == "add"
