from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

DEFAULT_INCLUDE = [
    "org",
    "applications",
    "groups",
    "group_rules",
    "policies",
    "identity_providers",
    "authorization_servers",
    "trusted_origins",
    "network_zones",
    "domains",
    "brands",
    "authenticators",
    "event_hooks",
    "inline_hooks",
]


@dataclass(frozen=True)
class InventoryConfig:
    backup_dir: Path
    output_dir: Path = Path("output")
    include: tuple[str, ...] = tuple(DEFAULT_INCLUDE)
    write_csv: bool = True
    write_json: bool = True
    write_markdown: bool = True
    strict_mode: bool = False
    fail_on_manifest_errors: bool = False
    max_preview_chars: int = 250


def _load_json_file(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError as exc:
        raise ValueError(f"Config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Config file is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Config JSON must be an object.")
    return data


def load_config(config_path: str | None = None, overrides: dict | None = None) -> InventoryConfig:
    raw: dict = {}
    if config_path:
        raw.update(_load_json_file(Path(config_path)))
    if overrides:
        raw.update({k: v for k, v in overrides.items() if v is not None})

    backup_dir = raw.get("backupDir") or raw.get("backup_dir")
    if not backup_dir:
        raise ValueError("backupDir is required. Pass --backup-dir or provide it in the config file.")

    include = raw.get("include", DEFAULT_INCLUDE)
    if isinstance(include, str):
        include = [part.strip() for part in include.split(",") if part.strip()]
    if not isinstance(include, list) or not all(isinstance(x, str) for x in include):
        raise ValueError("include must be a list of strings or a comma-separated string.")

    return InventoryConfig(
        backup_dir=Path(str(backup_dir)),
        output_dir=Path(str(raw.get("outputDir") or raw.get("output_dir") or "output")),
        include=tuple(include),
        write_csv=bool(raw.get("writeCsv", raw.get("write_csv", True))),
        write_json=bool(raw.get("writeJson", raw.get("write_json", True))),
        write_markdown=bool(raw.get("writeMarkdown", raw.get("write_markdown", True))),
        strict_mode=bool(raw.get("strictMode", raw.get("strict_mode", False))),
        fail_on_manifest_errors=bool(raw.get("failOnManifestErrors", raw.get("fail_on_manifest_errors", False))),
        max_preview_chars=int(raw.get("maxPreviewChars", raw.get("max_preview_chars", 250))),
    )
