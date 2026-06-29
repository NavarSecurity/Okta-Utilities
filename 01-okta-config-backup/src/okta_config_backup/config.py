from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_INCLUDE = [
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
]

DEFAULT_POLICY_TYPES = [
    "OKTA_SIGN_ON",
    "PASSWORD",
    "MFA_ENROLL",
    "IDP_DISCOVERY",
    "PROFILE_ENROLLMENT",
]

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
class BackupConfig:
    org_url: str
    api_token: str | None
    output_dir: Path = Path("output")
    include: list[str] = field(default_factory=lambda: list(DEFAULT_INCLUDE))
    policy_types: list[str] = field(default_factory=lambda: list(DEFAULT_POLICY_TYPES))
    page_limit: int = 200
    timeout_seconds: int = 30
    max_retries: int = 4
    retry_base_seconds: float = 1.0
    fail_fast: bool = False
    redaction_enabled: bool = True


def load_dotenv(path: Path) -> None:
    """Small .env loader to avoid requiring python-dotenv."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_json_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_org_url(value: str | None) -> str:
    if not value:
        raise ValueError("Okta org URL is required. Set OKTA_ORG_URL or orgUrl in the config file.")

    normalized = value.strip().rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Okta org URL must be an HTTPS URL such as https://your-org.okta.com")
    return normalized


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


def as_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    if value is None:
        return default
    parsed = float(value)
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"Expected number between {minimum} and {maximum}, got {parsed}")
    return parsed


def parse_csv(value: str | None) -> list[str] | None:
    if value is None:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or None


def validate_include(include: list[str]) -> list[str]:
    unknown = sorted(set(include) - KNOWN_RESOURCES)
    if unknown:
        raise ValueError(f"Unknown resource name(s): {', '.join(unknown)}")
    return include


def build_config(
    config_path: Path | None,
    cli_output_dir: Path | None = None,
    cli_include: str | None = None,
    cli_policy_types: str | None = None,
    dry_run: bool = False,
) -> BackupConfig:
    load_dotenv(Path.cwd() / ".env")
    if config_path:
        load_dotenv(config_path.parent / ".env")

    raw = load_json_config(config_path)

    org_url = normalize_org_url(os.getenv("OKTA_ORG_URL") or raw.get("orgUrl"))
    token_env_var = str(raw.get("apiTokenEnvVar") or "OKTA_API_TOKEN")
    api_token = os.getenv(token_env_var)

    if not dry_run and not api_token:
        raise ValueError(
            f"Okta API token is required for backup runs. Set {token_env_var} in your environment or .env file."
        )

    include = parse_csv(cli_include) or raw.get("include") or list(DEFAULT_INCLUDE)
    if not isinstance(include, list) or not all(isinstance(item, str) for item in include):
        raise ValueError("include must be a list of resource names or a comma-separated CLI value.")
    include = validate_include(include)

    policy_types = parse_csv(cli_policy_types) or raw.get("policyTypes") or list(DEFAULT_POLICY_TYPES)
    if not isinstance(policy_types, list) or not all(isinstance(item, str) for item in policy_types):
        raise ValueError("policyTypes must be a list of strings or a comma-separated CLI value.")

    output_dir_value = cli_output_dir or raw.get("outputDir") or "output"

    cfg = BackupConfig(
        org_url=org_url,
        api_token=api_token,
        output_dir=Path(output_dir_value),
        include=include,
        policy_types=policy_types,
        page_limit=as_int(raw.get("pageLimit"), 200, 1, 1000),
        timeout_seconds=as_int(raw.get("timeoutSeconds"), 30, 1, 300),
        max_retries=as_int(raw.get("maxRetries"), 4, 0, 10),
        retry_base_seconds=as_float(raw.get("retryBaseSeconds"), 1.0, 0.1, 60.0),
        fail_fast=as_bool(raw.get("failFast"), False),
        redaction_enabled=as_bool(raw.get("redactionEnabled"), True),
    )
    return cfg


def without_token(cfg: BackupConfig) -> BackupConfig:
    """Return config copy safe for logs/manifests."""
    return replace(cfg, api_token=None)
