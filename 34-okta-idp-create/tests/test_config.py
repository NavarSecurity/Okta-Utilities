import json
from pathlib import Path

import pytest

from okta_idp_create.config import ConfigError, load_config, load_idp_input


def test_load_config(tmp_path: Path):
    input_file = tmp_path / "idps.json"
    input_file.write_text('{"identityProviders": []}', encoding="utf-8")
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"inputFile": str(input_file), "onExisting": "skip"}), encoding="utf-8")

    config = load_config(config_file)

    assert config.input_file == input_file
    assert config.on_existing == "skip"
    assert config.match_by == "name"


def test_invalid_on_existing(tmp_path: Path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"inputFile": "x", "onExisting": "replace"}), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(config_file)


def test_load_idp_input_requires_array(tmp_path: Path):
    input_file = tmp_path / "idps.json"
    input_file.write_text('{"identityProviders": {}}', encoding="utf-8")
    with pytest.raises(ConfigError):
        load_idp_input(input_file)
