from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def load_dotenv(path: str | os.PathLike[str]) -> None:
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


def load_json_file(path: str | os.PathLike[str]) -> Any:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_config(path: str | os.PathLike[str]) -> dict[str, Any]:
    config = load_json_file(path)
    if not isinstance(config, dict):
        raise ValueError("Config file must contain a JSON object.")
    config.setdefault("outputDir", "output")
    config.setdefault("request", {})
    config.setdefault("okta", {})
    config.setdefault("export", {})
    config.setdefault("compare", {})
    config.setdefault("import", {})
    config.setdefault("manage", {})
    return config


def resolve_env_value(config: dict[str, Any], env_key_name: str, default_env_name: str) -> str:
    okta_cfg = config.get("okta", {})
    env_name = okta_cfg.get(env_key_name, default_env_name)
    value = os.environ.get(env_name)
    if not value:
        raise ValueError(f"Missing required environment variable: {env_name}")
    return value.strip()


def normalize_org_url(org_url: str) -> str:
    org_url = org_url.strip().rstrip("/")
    if not org_url.startswith("https://"):
        raise ValueError("OKTA_ORG_URL must start with https://")
    if org_url.endswith("/admin") or "/api/" in org_url:
        raise ValueError("OKTA_ORG_URL must be the base org URL, not /admin or /api.")
    return org_url
