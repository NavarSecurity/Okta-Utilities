import json
from pathlib import Path

from okta_scim_provisioning_tester.config import load_config, load_test_plan


def test_load_config(monkeypatch, tmp_path):
    monkeypatch.setenv("SCIM_BASE_URL", "https://example.com/scim/v2")
    monkeypatch.setenv("SCIM_AUTH_TYPE", "none")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "operation": "test",
        "outputDirectory": str(tmp_path / "output"),
        "planFile": str(tmp_path / "plan.json"),
        "operations": {"createUser": True}
    }), encoding="utf-8")
    config = load_config(config_path)
    assert config.operation == "test"
    assert config.base_url == "https://example.com/scim/v2"
    assert config.auth_type == "none"


def test_discovery_disables_mutations(monkeypatch, tmp_path):
    monkeypatch.setenv("SCIM_BASE_URL", "https://example.com/scim/v2")
    monkeypatch.setenv("SCIM_AUTH_TYPE", "none")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "operation": "discovery",
        "operations": {"createUser": True, "groupPush": True}
    }), encoding="utf-8")
    config = load_config(config_path)
    assert config.operations["createUser"] is False
    assert config.operations["groupPush"] is False


def test_load_test_plan(tmp_path):
    path = tmp_path / "plan.json"
    path.write_text('{"testUser": {"userName": "test@example.com"}}', encoding="utf-8")
    plan = load_test_plan(path)
    assert plan["testUser"]["userName"] == "test@example.com"
