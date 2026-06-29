from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

KNOWN_RESOURCES = {
    "org",
    "applications",
    "groups",
    "group_rules",
    "policies",
    "identity_providers",
    "authorization_servers",
    "event_hooks",
    "inline_hooks",
    "network_zones",
    "trusted_origins",
    "brands",
    "domains",
    "authenticators",
    "features",
    "user_schema",
}


@dataclass(frozen=True)
class ValidatorConfig:
    backup_dir: Path
    output_dir: Path = Path("output")
    expected_resources: list[str] | None = None
    required_resources: list[str] | None = None
    allow_missing_files_for_errored_resources: bool = True
    require_no_resource_errors: bool = False
    require_redaction_enabled: bool = True
    strict_mode: bool = False
    fail_on_warnings: bool = False
    sensitive_scan_enabled: bool = True
    max_sensitive_findings: int = 50


def load_json_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Config file must contain a JSON object.")
    return data


def as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def as_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    if value is None:
        return default
    parsed = int(value)
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"Expected integer between {minimum} and {maximum}, got {parsed}")
    return parsed


def as_string_list(value: Any, field_name: str, allow_manifest: bool = False) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, list) and all(isinstance(item, str) for item in value):
        items = list(value)
    else:
        raise ValueError(f"{field_name} must be a list of strings or a comma-separated string.")

    allowed = set(KNOWN_RESOURCES)
    if allow_manifest:
        allowed.add("manifest")
    unknown = sorted(set(items) - allowed)
    if unknown:
        raise ValueError(f"Unknown {field_name} value(s): {', '.join(unknown)}")
    return items


def build_config(
    config_path: Path | None,
    cli_backup_dir: Path | None = None,
    cli_output_dir: Path | None = None,
    cli_strict: bool = False,
    cli_fail_on_warnings: bool = False,
) -> ValidatorConfig:
    raw = load_json_config(config_path)

    backup_dir_value = cli_backup_dir or raw.get("backupDir") or raw.get("backup_dir")
    if not backup_dir_value:
        raise ValueError("Backup directory is required. Set backupDir in config or pass --backup-dir.")

    output_dir_value = cli_output_dir or raw.get("outputDir") or raw.get("output_dir") or "output"

    expected_resources = as_string_list(raw.get("expectedResources") or raw.get("expected_resources"), "expectedResources")
    required_resources = as_string_list(
        raw.get("requiredResources") or raw.get("required_resources") or ["manifest"],
        "requiredResources",
        allow_manifest=True,
    )

    strict_mode = cli_strict or as_bool(raw.get("strictMode") or raw.get("strict_mode"), False)
    fail_on_warnings = cli_fail_on_warnings or as_bool(raw.get("failOnWarnings") or raw.get("fail_on_warnings"), False)

    cfg = ValidatorConfig(
        backup_dir=Path(str(backup_dir_value)),
        output_dir=Path(str(output_dir_value)),
        expected_resources=expected_resources,
        required_resources=required_resources,
        allow_missing_files_for_errored_resources=as_bool(
            raw.get("allowMissingFilesForErroredResources")
            if "allowMissingFilesForErroredResources" in raw
            else raw.get("allow_missing_files_for_errored_resources"),
            True,
        ),
        require_no_resource_errors=as_bool(
            raw.get("requireNoResourceErrors") if "requireNoResourceErrors" in raw else raw.get("require_no_resource_errors"),
            False,
        ),
        require_redaction_enabled=as_bool(
            raw.get("requireRedactionEnabled") if "requireRedactionEnabled" in raw else raw.get("require_redaction_enabled"),
            True,
        ),
        strict_mode=strict_mode,
        fail_on_warnings=fail_on_warnings,
        sensitive_scan_enabled=as_bool(
            raw.get("sensitiveScanEnabled") if "sensitiveScanEnabled" in raw else raw.get("sensitive_scan_enabled"),
            True,
        ),
        max_sensitive_findings=as_int(
            raw.get("maxSensitiveFindings") if "maxSensitiveFindings" in raw else raw.get("max_sensitive_findings"),
            50,
            1,
            1000,
        ),
    )

    if cfg.strict_mode:
        cfg = replace(
            cfg,
            require_no_resource_errors=True,
            allow_missing_files_for_errored_resources=False,
            fail_on_warnings=True,
        )
    return cfg
