import json
from pathlib import Path

import pytest

from okta_group_rule_create.config import ConfigError, load_config


def write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def base_config():
    return {
        "targetOrgUrl": "https://example.okta.com",
        "apiToken": "token",
        "settings": {"maxRulesPerRun": 5},
        "rules": [
            {
                "name": "Rule - Test",
                "approved": True,
                "expression": "user.department == \"Test\"",
                "targetGroupIds": ["00g123"],
            }
        ],
    }


def test_load_config_parses_rule(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    config = load_config(write_config(tmp_path, base_config()))
    assert config.target_org_url == "https://example.okta.com"
    assert config.rules[0].name == "Rule - Test"
    assert config.rules[0].target_group_ids == ["00g123"]


def test_rejects_admin_url(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    data = base_config()
    data["targetOrgUrl"] = "https://example-admin.okta.com"
    with pytest.raises(ConfigError):
        load_config(write_config(tmp_path, data))


def test_requires_target_group(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    data = base_config()
    data["rules"][0]["targetGroupIds"] = []
    data["rules"][0]["targetGroupNames"] = []
    with pytest.raises(ConfigError):
        load_config(write_config(tmp_path, data))


def test_max_rules_limit(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    data = base_config()
    data["settings"]["maxRulesPerRun"] = 1
    data["rules"].append({
        "name": "Rule - Test 2",
        "approved": True,
        "expression": "user.department == \"Two\"",
        "targetGroupIds": ["00g456"],
    })
    with pytest.raises(ConfigError):
        load_config(write_config(tmp_path, data))
