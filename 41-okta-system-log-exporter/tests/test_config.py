import json
from pathlib import Path

import pytest

from okta_system_log_exporter.config import ConfigError, load_config


def write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_load_config_defaults(tmp_path):
    path = write_config(tmp_path, {})
    cfg = load_config(path)
    assert cfg.output_directory == "output"
    assert cfg.limit == 1000
    assert cfg.max_events == 5000
    assert cfg.sort_order == "ASCENDING"


def test_limit_too_large_fails(tmp_path):
    path = write_config(tmp_path, {"limit": 5000})
    with pytest.raises(ConfigError):
        load_config(path)


def test_since_after_until_fails(tmp_path):
    path = write_config(
        tmp_path,
        {
            "since": "2026-07-16T10:00:00Z",
            "until": "2026-07-16T09:00:00Z",
        },
    )
    with pytest.raises(ConfigError):
        load_config(path)
