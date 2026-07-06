from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


class InputError(ValueError):
    pass


def flatten_dict(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            result.update(flatten_dict(value, full_key))
        elif isinstance(value, list):
            result[full_key] = json.dumps(value, sort_keys=True)
        else:
            result[full_key] = value
    return result


def read_users(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise InputError(f"Input file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return read_users_csv(path)
    if suffix == ".json":
        return read_users_json(path)
    raise InputError(f"Unsupported input format for {path}. Use .csv or .json")


def read_users_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise InputError(f"CSV has no header row: {path}")
        rows = []
        for idx, row in enumerate(reader, start=2):
            clean = {str(k).strip(): (v if v is not None else "") for k, v in row.items() if k is not None}
            clean["__row_number"] = idx
            rows.append(clean)
        return rows


def _extract_user_list(data: Any) -> list[Any]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("users", "items", "data", "results"):
            if isinstance(data.get(key), list):
                return data[key]
    raise InputError("JSON input must be a list of users or an object containing users/items/data/results")


def read_users_json(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InputError(f"JSON input is not valid: {path}: {exc}") from exc
    users = _extract_user_list(data)
    out = []
    for idx, user in enumerate(users, start=1):
        if not isinstance(user, dict):
            continue
        flat = flatten_dict(user)
        flat["__row_number"] = idx
        out.append(flat)
    return out


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)
        fieldnames = keys or ["message"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
