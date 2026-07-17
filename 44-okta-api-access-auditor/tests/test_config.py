import json
from pathlib import Path

from okta_api_access_auditor.config import load_config


def test_load_config_defaults(tmp_path: Path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({}), encoding="utf-8")
    config = load_config(config_path)
    assert config.output_directory == "output"
    assert config.include_api_tokens is True
    assert config.app_selection.mode == "service"
    assert "okta.users.manage" in config.risk_rules.high_risk_scopes


def test_load_config_custom_values(tmp_path: Path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"includeApiTokens": False, "appSelection": {"mode": "file", "appFile": "input/apps.txt"}}),
        encoding="utf-8",
    )
    config = load_config(config_path)
    assert config.include_api_tokens is False
    assert config.app_selection.mode == "file"
