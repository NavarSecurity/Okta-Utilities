import json
import pytest
from okta_app_provisioning_exporter.config import load_config


def test_load_config_defaults(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"outputDirectory":"output"}), encoding="utf-8")
    cfg = load_config(p)
    assert cfg.output_directory == "output"
    assert cfg.include_app_schemas is True
    assert cfg.app_selection.mode == "all"


def test_invalid_selection_mode(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"appSelection":{"mode":"bad"}}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(p)
