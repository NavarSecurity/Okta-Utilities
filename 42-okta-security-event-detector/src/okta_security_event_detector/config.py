from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import read_json

DEFAULT_CONFIG: dict[str, Any] = {
    "inputFile": "input/system_log_events_full.json",
    "outputDirectory": "output",
    "redactSensitiveValues": True,
    "includeLowSeverity": True,
    "includeInformationalFindings": False,
    "filters": {
        "eventTypes": [],
        "actors": [],
        "excludeActors": [],
        "ipAddresses": [],
        "startTime": None,
        "endTime": None,
    },
    "detections": {
        "failedSignInSpike": {"enabled": True, "threshold": 5, "severity": "medium"},
        "mfaFailureSpike": {"enabled": True, "threshold": 3, "severity": "high"},
        "suspiciousCountry": {"enabled": True, "allowedCountries": ["United States"], "severity": "medium"},
        "multipleCountriesPerActor": {"enabled": True, "threshold": 2, "severity": "medium"},
        "suspiciousIpAddresses": {"enabled": True, "ipAddresses": [], "severity": "high"},
        "adminActivity": {"enabled": True, "severity": "high"},
        "policyChanges": {"enabled": True, "severity": "high"},
        "factorChanges": {"enabled": True, "severity": "high"},
        "apiTokenActivity": {"enabled": True, "severity": "high"},
        "userLifecycleChanges": {"enabled": True, "severity": "medium"},
        "appConfigurationChanges": {"enabled": True, "severity": "medium"},
        "rateLimitEvents": {"enabled": True, "severity": "high"},
    },
}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str | Path) -> dict[str, Any]:
    raw = read_json(path)
    if not isinstance(raw, dict):
        raise ValueError("Configuration file must contain a JSON object.")
    config = deep_merge(DEFAULT_CONFIG, raw)
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    if not config.get("inputFile"):
        raise ValueError("config.inputFile is required.")
    if not config.get("outputDirectory"):
        raise ValueError("config.outputDirectory is required.")
    detections = config.get("detections", {})
    for rule_name, rule_config in detections.items():
        if not isinstance(rule_config, dict):
            raise ValueError(f"detections.{rule_name} must be an object.")
        severity = rule_config.get("severity")
        if severity and severity not in {"info", "low", "medium", "high", "critical"}:
            raise ValueError(f"detections.{rule_name}.severity has invalid value: {severity}")
        threshold = rule_config.get("threshold")
        if threshold is not None and int(threshold) < 1:
            raise ValueError(f"detections.{rule_name}.threshold must be greater than zero.")
