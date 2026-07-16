from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


DEFAULT_OPERATIONS = {
    "serviceProviderConfig": True,
    "schemas": True,
    "resourceTypes": True,
    "createUser": True,
    "updateUser": True,
    "deactivateUser": True,
    "createGroup": True,
    "groupPush": True,
    "cleanup": False,
}


@dataclass(frozen=True)
class AppConfig:
    operation: str
    output_directory: Path
    plan_file: Path
    base_url: str
    auth_type: str
    timeout_seconds: int
    verify_ssl: bool
    continue_on_error: bool
    redact_sensitive_values: bool
    operations: dict[str, bool]
    cleanup: dict[str, bool]


def load_json(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Config file not found: {target}")
    with target.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_test_plan(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"SCIM test plan not found: {target}")
    with target.open("r", encoding="utf-8") as handle:
        plan = json.load(handle)
    if not isinstance(plan, dict):
        raise ValueError("SCIM test plan must be a JSON object.")
    return plan


def load_config(config_path: str | Path) -> AppConfig:
    load_dotenv()
    raw = load_json(config_path)

    operation = str(raw.get("operation", "test")).strip().lower()
    if operation not in {"test", "discovery"}:
        raise ValueError("operation must be one of: test, discovery")

    base_url_env = raw.get("baseUrlEnv", "SCIM_BASE_URL")
    base_url = os.getenv(str(base_url_env), "").strip().rstrip("/")
    if not base_url:
        raise ValueError(f"Missing SCIM base URL. Set {base_url_env} in .env or environment variables.")

    auth_type_env = raw.get("authTypeEnv", "SCIM_AUTH_TYPE")
    auth_type = os.getenv(str(auth_type_env), "bearer").strip().lower()
    if auth_type not in {"bearer", "basic", "none"}:
        raise ValueError("SCIM_AUTH_TYPE must be one of: bearer, basic, none")

    operations = DEFAULT_OPERATIONS.copy()
    operations.update(raw.get("operations", {}) or {})

    if operation == "discovery":
        operations["createUser"] = False
        operations["updateUser"] = False
        operations["deactivateUser"] = False
        operations["createGroup"] = False
        operations["groupPush"] = False
        operations["cleanup"] = False

    cleanup = {
        "deleteUserAfterTest": False,
        "deleteGroupAfterTest": False,
    }
    cleanup.update(raw.get("cleanup", {}) or {})

    return AppConfig(
        operation=operation,
        output_directory=Path(raw.get("outputDirectory", "output")),
        plan_file=Path(raw.get("planFile", "input/scim_test_plan.json")),
        base_url=base_url,
        auth_type=auth_type,
        timeout_seconds=int(raw.get("timeoutSeconds", 30)),
        verify_ssl=bool(raw.get("verifySsl", True)),
        continue_on_error=bool(raw.get("continueOnError", True)),
        redact_sensitive_values=bool(raw.get("redactSensitiveValues", True)),
        operations={key: bool(value) for key, value in operations.items()},
        cleanup={key: bool(value) for key, value in cleanup.items()},
    )
