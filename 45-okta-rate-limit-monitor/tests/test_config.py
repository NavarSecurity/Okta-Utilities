import json

import pytest

from okta_rate_limit_monitor.config import ConfigError, load_config


def test_load_config(tmp_path):
    config = {
        "outputDirectory": "output",
        "probeEndpoints": [{"name": "users", "method": "GET", "path": "/api/v1/users"}],
        "plannedOperations": [{"name": "backup", "endpoint": "/api/v1/users", "estimatedRequests": 10, "windowMinutes": 1}],
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    loaded = load_config(path)
    assert loaded.output_directory == "output"
    assert loaded.probe_endpoints[0]["name"] == "users"
    assert loaded.planned_operations[0]["estimatedRequests"] == 10


def test_load_config_rejects_non_get_probe(tmp_path):
    config = {"probeEndpoints": [{"name": "bad", "method": "POST", "path": "/api/v1/users"}]}
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_load_config_rejects_bad_planned_operation(tmp_path):
    config = {"plannedOperations": [{"name": "bad", "endpoint": "/api/v1/users", "estimatedRequests": -1, "windowMinutes": 1}]}
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)
