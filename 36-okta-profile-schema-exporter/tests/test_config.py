import json
from pathlib import Path

import pytest

from okta_profile_schema_exporter.config import ConfigError, load_config, validate_runtime_config


def test_load_config_defaults(tmp_path: Path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({}), encoding="utf-8")
    config = load_config(path)
    assert config.output_directory == "output"
    assert config.include_user_schemas is True
    assert config.user_schema_ids == ["default"]
    assert config.app_selection.mode == "all"
    assert config.skip_okta_system_apps is True
    assert "saasure" in config.excluded_app_names


def test_invalid_app_selection_mode(tmp_path: Path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"appSelection": {"mode": "bad"}}), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_validate_names_requires_names(tmp_path: Path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"appSelection": {"mode": "names", "appNames": []}}), encoding="utf-8")
    config = load_config(path)
    with pytest.raises(ConfigError):
        validate_runtime_config(config, require_okta=False)
