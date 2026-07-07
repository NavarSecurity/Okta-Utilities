import json
from pathlib import Path

import pytest

from okta_group_create.config import ConfigError, load_config, normalize_org_url


def test_reject_admin_url():
    with pytest.raises(ConfigError):
        normalize_org_url("https://example-admin.okta.com")


def test_load_config(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"targetOrgUrl": "https://example.okta.com", "groupsFile": "input/groups.csv"}))
    cfg = load_config(p)
    assert cfg.target_org_url == "https://example.okta.com"
    assert cfg.groups_file == Path("input/groups.csv")
