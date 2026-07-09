from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List
import json
import os

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

from dotenv import load_dotenv


class ConfigError(Exception):
    pass


@dataclass
class AppConfig:
    org_url: str
    api_token: str
    users_file: str
    settings: Dict[str, Any] = field(default_factory=dict)
    columns: Dict[str, str] = field(default_factory=dict)


DEFAULT_COLUMNS = {
    "userId": "userId",
    "login": "login",
    "email": "email",
    "action": "action",
    "factorId": "factorId",
    "factorType": "factorType",
    "provider": "provider",
    "authenticatorEnrollmentId": "authenticatorEnrollmentId",
    "approved": "approved",
    "reason": "reason",
}

DEFAULT_SETTINGS = {
    "defaultAction": "reset_all_factors",
    "requireApproved": True,
    "approvedValues": ["true", "yes", "y", "approved"],
    "requireReason": True,
    "maxUsersPerRun": 25,
    "allowResetAllFactors": True,
    "allowDeleteSelectedFactors": True,
    "allowDeleteAuthenticatorEnrollments": False,
    "verifyUsersBeforeAction": True,
    "skipProtectedLogins": True,
    "protectedLoginPatterns": ["admin", "breakglass", "break-glass", "service", "svc", "root", "superadmin"],
    "continueOnError": False,
    "requestTimeoutSeconds": 30,
    "maxRetries": 3,
}


def _load_json_or_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise ConfigError("PyYAML is required to load YAML config files.")
        data = yaml.safe_load(text) or {}
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ConfigError("Config root must be an object.")
    return data


def normalize_org_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if not url:
        raise ConfigError("Okta org URL is required.")
    lowered = url.lower()
    if "-admin.okta" in lowered or "-admin.oktapreview" in lowered:
        raise ConfigError("Use the Okta org URL, not the Admin Console -admin URL.")
    if lowered.endswith("/admin") or "/admin/" in lowered or "/api/v1" in lowered:
        raise ConfigError("Use only the Okta org base URL, not /admin or /api/v1.")
    if not lowered.startswith("https://"):
        raise ConfigError("Okta org URL must start with https://")
    return url


def load_config(config_path: str) -> AppConfig:
    load_dotenv()
    path = Path(config_path)
    data = _load_json_or_yaml(path)

    org_url = os.getenv("OKTA_ORG_URL") or data.get("orgUrl") or data.get("targetOrgUrl")
    api_token = os.getenv("OKTA_API_TOKEN") or data.get("apiToken") or ""
    if not api_token:
        raise ConfigError("OKTA_API_TOKEN is required in .env or config.")

    input_cfg = data.get("input") or {}
    users_file = input_cfg.get("usersFile") or data.get("usersFile") or "input/mfa-reset-users.csv"

    settings = dict(DEFAULT_SETTINGS)
    settings.update(data.get("settings") or {})

    columns = dict(DEFAULT_COLUMNS)
    columns.update(data.get("columns") or {})

    return AppConfig(
        org_url=normalize_org_url(str(org_url or "")),
        api_token=str(api_token),
        users_file=str(users_file),
        settings=settings,
        columns=columns,
    )
