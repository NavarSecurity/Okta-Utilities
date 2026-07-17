from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    pass


def load_dotenv(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def read_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Config file not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in config file {p}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("Config file must contain a JSON object.")
    return data


def _int_value(data: dict[str, Any], key: str, default: int) -> int:
    value = data.get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{key} must be an integer.") from exc


def _bool_value(data: dict[str, Any], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if isinstance(value, bool):
        return value
    raise ConfigError(f"{key} must be true or false.")


@dataclass
class MonitorConfig:
    output_directory: str
    timeout_seconds: int
    redact_sensitive_values: bool
    continue_on_request_error: bool
    include_header_probes: bool
    include_system_log_events: bool
    include_planned_operation_estimate: bool
    lookback_hours: int
    system_log_filters: list[str]
    probe_endpoints: list[dict[str, Any]]
    planned_operations: list[dict[str, Any]]
    risk_thresholds: dict[str, Any]


def load_config(config_path: str | Path) -> MonitorConfig:
    data = read_json(config_path)

    output_directory = data.get("outputDirectory", "output")
    if not isinstance(output_directory, str) or not output_directory.strip():
        raise ConfigError("outputDirectory must be a non-empty string.")

    system_log_filters = data.get("systemLogFilters", [])
    if not isinstance(system_log_filters, list) or not all(isinstance(item, str) for item in system_log_filters):
        raise ConfigError("systemLogFilters must be a list of strings.")

    probe_endpoints = data.get("probeEndpoints", [])
    if not isinstance(probe_endpoints, list):
        raise ConfigError("probeEndpoints must be a list.")
    for endpoint in probe_endpoints:
        if not isinstance(endpoint, dict):
            raise ConfigError("Each probe endpoint must be an object.")
        if not endpoint.get("name") or not endpoint.get("path"):
            raise ConfigError("Each probe endpoint must include name and path.")
        method = str(endpoint.get("method", "GET")).upper()
        if method != "GET":
            raise ConfigError("Only GET probe endpoints are supported.")

    planned_operations = data.get("plannedOperations", [])
    if not isinstance(planned_operations, list):
        raise ConfigError("plannedOperations must be a list.")
    for operation in planned_operations:
        if not isinstance(operation, dict):
            raise ConfigError("Each planned operation must be an object.")
        if not operation.get("name") or not operation.get("endpoint"):
            raise ConfigError("Each planned operation must include name and endpoint.")
        try:
            estimated = int(operation.get("estimatedRequests", 0))
            window = int(operation.get("windowMinutes", 1))
        except (TypeError, ValueError) as exc:
            raise ConfigError("plannedOperations estimatedRequests and windowMinutes must be integers.") from exc
        if estimated < 0 or window <= 0:
            raise ConfigError("plannedOperations estimatedRequests must be >= 0 and windowMinutes must be > 0.")

    risk_thresholds = data.get("riskThresholds", {})
    if not isinstance(risk_thresholds, dict):
        raise ConfigError("riskThresholds must be an object.")

    return MonitorConfig(
        output_directory=output_directory,
        timeout_seconds=_int_value(data, "timeoutSeconds", 30),
        redact_sensitive_values=_bool_value(data, "redactSensitiveValues", True),
        continue_on_request_error=_bool_value(data, "continueOnRequestError", True),
        include_header_probes=_bool_value(data, "includeHeaderProbes", True),
        include_system_log_events=_bool_value(data, "includeSystemLogEvents", True),
        include_planned_operation_estimate=_bool_value(data, "includePlannedOperationEstimate", True),
        lookback_hours=_int_value(data, "lookbackHours", 24),
        system_log_filters=system_log_filters,
        probe_endpoints=probe_endpoints,
        planned_operations=planned_operations,
        risk_thresholds=risk_thresholds,
    )


def get_okta_env() -> tuple[str, str]:
    load_dotenv()
    org_url = os.environ.get("OKTA_ORG_URL", "").strip().rstrip("/")
    api_token = os.environ.get("OKTA_API_TOKEN", "").strip()
    if not org_url:
        raise ConfigError("OKTA_ORG_URL is not set. Update .env or the environment.")
    if not api_token:
        raise ConfigError("OKTA_API_TOKEN is not set. Update .env or the environment.")
    if org_url.endswith("/api/v1"):
        raise ConfigError("OKTA_ORG_URL should be the org base URL, not a /api/v1 path.")
    return org_url, api_token
