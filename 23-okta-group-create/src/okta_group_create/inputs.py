from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import yaml


class InputError(ValueError):
    pass


def load_group_rows(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        raise InputError(f"Groups input file not found: {p}")
    suffix = p.suffix.lower()
    if suffix == ".csv":
        return _load_csv(p)
    if suffix == ".json":
        return _load_json(p)
    if suffix in {".yaml", ".yml"}:
        return _load_yaml(p)
    raise InputError("groupsFile must be a .csv, .json, .yaml, or .yml file.")


def _load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise InputError("CSV file has no header row.")
        return [dict(row) for row in reader]


def _load_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("groups"), list):
        return data["groups"]
    raise InputError("JSON input must be a list of groups or an object with a groups list.")


def _load_yaml(path: Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("groups"), list):
        return data["groups"]
    raise InputError("YAML input must be a list of groups or an object with a groups list.")
