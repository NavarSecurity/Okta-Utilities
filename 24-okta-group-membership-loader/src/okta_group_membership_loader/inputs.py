from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import yaml

from .config import LoaderConfig
from .models import MembershipRequest


class InputError(ValueError):
    pass


def _detect_format(path: Path, configured: str) -> str:
    if configured and configured != "auto":
        return configured.lower()
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix == ".json":
        return "json"
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    raise InputError(f"Unable to detect input format for {path}. Use input.format in config.")


def _get(row: dict[str, Any], column_name: str) -> str:
    value = row.get(column_name, "")
    if value is None:
        return ""
    return str(value).strip()


def _record_to_request(row_number: int, row: dict[str, Any], cfg: LoaderConfig) -> MembershipRequest:
    c = cfg.columns
    action = _get(row, c["action"]) or cfg.default_action
    return MembershipRequest(
        row_number=row_number,
        action=action.lower().strip(),
        group_id=_get(row, c["groupId"]),
        group_name=_get(row, c["groupName"]),
        user_id=_get(row, c["userId"]),
        login=_get(row, c["login"]),
        email=_get(row, c["email"]),
        approved=_get(row, c["approved"]),
        reason=_get(row, c["reason"]),
        source=row,
    )


def read_membership_requests(cfg: LoaderConfig) -> list[MembershipRequest]:
    path = Path(cfg.membership_file)
    if not path.exists():
        raise InputError(f"Membership input file not found: {path}")
    fmt = _detect_format(path, cfg.input_format)

    rows: list[dict[str, Any]]
    if fmt == "csv":
        with path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise InputError("CSV file has no header row")
            rows = [dict(row) for row in reader]
    elif fmt == "json":
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            rows = raw.get("memberships") or raw.get("rows") or raw.get("items") or []
        elif isinstance(raw, list):
            rows = raw
        else:
            raise InputError("JSON input must be a list or an object with memberships, rows, or items")
    elif fmt == "yaml":
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        if isinstance(raw, dict):
            rows = raw.get("memberships") or raw.get("rows") or raw.get("items") or []
        elif isinstance(raw, list):
            rows = raw
        else:
            raise InputError("YAML input must be a list or an object with memberships, rows, or items")
    else:
        raise InputError(f"Unsupported input format: {fmt}")

    if not isinstance(rows, list):
        raise InputError("Membership input must resolve to a list of records")

    requests: list[MembershipRequest] = []
    for idx, row in enumerate(rows, start=2 if fmt == "csv" else 1):
        if not isinstance(row, dict):
            raise InputError(f"Input row {idx} is not an object")
        requests.append(_record_to_request(idx, row, cfg))
    return requests
