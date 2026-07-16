from okta_security_event_detector.config import deep_merge, load_config
from pathlib import Path
import json


def test_deep_merge_keeps_defaults():
    merged = deep_merge({"a": {"b": 1, "c": 2}}, {"a": {"b": 3}})
    assert merged["a"]["b"] == 3
    assert merged["a"]["c"] == 2


def test_load_config(tmp_path: Path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"inputFile": "x.json", "outputDirectory": "output"}), encoding="utf-8")
    config = load_config(config_path)
    assert config["inputFile"] == "x.json"
    assert "failedSignInSpike" in config["detections"]
