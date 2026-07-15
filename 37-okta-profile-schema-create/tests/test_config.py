import json
from pathlib import Path

import pytest

from okta_profile_schema_create.config import ConfigError, load_input_file, load_settings


def test_load_settings_defaults(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"inputFile": "input/test.json"}), encoding="utf-8")
    monkeypatch.setenv("OKTA_ORG_URL", "https://example.okta.com")
    monkeypatch.setenv("OKTA_API_TOKEN", "token")
    settings = load_settings(config_path)
    assert settings.input_file == Path("input/test.json")
    assert settings.on_existing == "skip"


def test_invalid_on_existing_rejected(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"onExisting": "merge"}), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_settings(config_path)


def test_load_input_requires_attributes(tmp_path):
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps({"items": []}), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_input_file(input_path)
