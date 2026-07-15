import json
from pathlib import Path

from okta_profile_mapping_exporter.config import load_config


def test_load_config_defaults(tmp_path: Path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"outputDirectory": "out"}), encoding="utf-8")
    config = load_config(config_path)
    assert config["outputDirectory"] == "out"
    assert config["limit"] == 200
    assert config["includeMappingDetails"] is True
