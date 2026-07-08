import json
from pathlib import Path

import pytest

from okta_group_rule_create.conditions import build_basic_condition_expression
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
                "name": "Rule - Basic",
                "approved": True,
                "basicCondition": {
                    "attribute": "department",
                    "operator": "equals",
                    "value": "Engineering",
                },
                "targetGroupIds": ["00g123"],
            }
        ],
    }


def test_basic_condition_equals_expression():
    expression = build_basic_condition_expression({
        "attribute": "department",
        "operator": "equals",
        "value": "Engineering",
    })
    assert expression == 'user.department == "Engineering"'


def test_basic_condition_contains_expression():
    expression = build_basic_condition_expression({
        "attribute": "email",
        "operator": "contains",
        "value": "@contractor.example.com",
    })
    assert expression == 'String.stringContains(user.email, "@contractor.example.com")'


def test_load_config_accepts_basic_condition(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    config = load_config(write_config(tmp_path, base_config()))
    assert config.rules[0].expression == 'user.department == "Engineering"'
    assert config.rules[0].condition_source == "basicCondition"


def test_load_config_accepts_multiple_basic_conditions(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    data = base_config()
    rule = data["rules"][0]
    rule.pop("basicCondition")
    rule["basicConditions"] = {
        "match": "all",
        "conditions": [
            {"attribute": "department", "operator": "equals", "value": "Engineering"},
            {"attribute": "title", "operator": "contains", "value": "Manager"},
        ],
    }
    config = load_config(write_config(tmp_path, data))
    assert config.rules[0].condition_source == "basicConditions"
    assert '(user.department == "Engineering")' in config.rules[0].expression
    assert '(String.stringContains(user.title, "Manager"))' in config.rules[0].expression
    assert "&&" in config.rules[0].expression


def test_rejects_expression_and_basic_condition_together(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    data = base_config()
    data["rules"][0]["expression"] = 'user.department == "Engineering"'
    with pytest.raises(ConfigError):
        load_config(write_config(tmp_path, data))


def test_rejects_bad_attribute():
    with pytest.raises(ConfigError):
        build_basic_condition_expression({
            "attribute": "department; evil()",
            "operator": "equals",
            "value": "Engineering",
        })
