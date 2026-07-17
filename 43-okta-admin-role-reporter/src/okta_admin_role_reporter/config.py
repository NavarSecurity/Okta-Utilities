from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "outputDirectory": "output",
    "includeUserRoleAssignments": True,
    "includeUserRoleTargets": True,
    "includeUserRoleGovernance": False,
    "includeGroupRoleAssignments": True,
    "includeGroupRoleTargets": True,
    "includeClientRoleAssignments": False,
    "includeClientRoleTargets": False,
    "includeCustomRoles": True,
    "includeCustomRolePermissions": True,
    "includeResourceSets": True,
    "includeResourceSetResources": True,
    "includeResourceSetBindings": True,
    "includeBindingMembers": True,
    "includePrivilegedGroupMembers": False,
    "continueOnRequestError": True,
    "redactSensitiveValues": True,
    "groupSelection": {
        "mode": "all",
        "groupIds": [],
        "groupNames": [],
        "groupFile": "input/groups.txt",
        "limit": 200,
    },
    "clientSelection": {
        "mode": "ids",
        "clientIds": [],
        "clientFile": "input/clients.txt",
    },
    "highPrivilegeRoles": [
        "SUPER_ADMIN",
        "ORG_ADMIN",
        "APP_ADMIN",
        "GROUP_ADMIN",
        "GROUP_MEMBERSHIP_ADMIN",
        "USER_ADMIN",
        "HELP_DESK_ADMIN",
        "MOBILE_ADMIN",
        "API_ACCESS_MANAGEMENT_ADMIN",
        "ACCESS_CERTIFICATIONS_ADMIN",
        "ACCESS_REQUESTS_ADMIN",
        "CUSTOM",
    ],
    "timeoutSeconds": 30,
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


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


def load_config(config_path: str | Path) -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        user_config = json.load(handle)
    config = _deep_merge(DEFAULT_CONFIG, user_config)
    config["configPath"] = str(path)
    return config


def get_okta_settings(require_credentials: bool = True) -> dict[str, str]:
    load_dotenv()
    org_url = os.getenv("OKTA_ORG_URL", "").strip().rstrip("/")
    token = os.getenv("OKTA_API_TOKEN", "").strip()
    if require_credentials:
        missing = []
        if not org_url:
            missing.append("OKTA_ORG_URL")
        if not token:
            missing.append("OKTA_API_TOKEN")
        if missing:
            raise ValueError(f"Missing required environment variable(s): {', '.join(missing)}")
    if org_url.endswith("/api/v1"):
        raise ValueError("OKTA_ORG_URL should be the org base URL only, not a URL ending in /api/v1")
    return {"org_url": org_url, "token": token}


def read_lines_file(path: str | Path) -> list[str]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    values: list[str] = []
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            values.append(line)
    return values
