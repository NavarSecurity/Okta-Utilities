from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class AppConfig:
    input_file: Path
    output_directory: Path
    check_existing: bool = True
    match_by: str = "name"
    on_existing: str = "skip"
    activate_after_create: bool = False
    redact_sensitive_values: bool = True
    timeout_seconds: int = 30


def load_json_file(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise ConfigError(f"File not found: {file_path}")
    try:
        with file_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {file_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Expected JSON object in {file_path}")
    return data


def load_config(path: str | Path) -> AppConfig:
    load_dotenv()
    data = load_json_file(path)

    required = ["inputFile"]
    missing = [key for key in required if not data.get(key)]
    if missing:
        raise ConfigError(f"Missing required config field(s): {', '.join(missing)}")

    match_by = data.get("matchBy", "name")
    if match_by != "name":
        raise ConfigError("Only matchBy='name' is currently supported")

    on_existing = data.get("onExisting", "skip")
    if on_existing not in {"skip", "error"}:
        raise ConfigError("onExisting must be 'skip' or 'error'")

    timeout_seconds = int(data.get("timeoutSeconds", 30))
    if timeout_seconds <= 0:
        raise ConfigError("timeoutSeconds must be greater than 0")

    return AppConfig(
        input_file=Path(data["inputFile"]),
        output_directory=Path(data.get("outputDirectory", "output")),
        check_existing=bool(data.get("checkExisting", True)),
        match_by=match_by,
        on_existing=on_existing,
        activate_after_create=bool(data.get("activateAfterCreate", False)),
        redact_sensitive_values=bool(data.get("redactSensitiveValues", True)),
        timeout_seconds=timeout_seconds,
    )


def load_idp_input(path: str | Path) -> list[dict[str, Any]]:
    data = load_json_file(path)
    idps = data.get("identityProviders")
    if not isinstance(idps, list):
        raise ConfigError("Input file must contain an identityProviders array")
    if not idps:
        raise ConfigError("identityProviders array is empty")
    for index, idp in enumerate(idps):
        if not isinstance(idp, dict):
            raise ConfigError(f"identityProviders[{index}] must be an object")
    return idps
