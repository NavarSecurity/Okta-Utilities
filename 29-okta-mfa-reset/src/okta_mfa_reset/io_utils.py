from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List
from datetime import datetime, timezone


def utc_run_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{stamp}"


def ensure_output_dir(base: str = "output") -> Path:
    path = Path(base) / utc_run_id("okta-mfa-reset")
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_csv(path: str) -> List[Dict[str, str]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Input CSV not found: {path}")
    with p.open(newline="", encoding="utf-8-sig") as f:
        return [dict(row) for row in csv.DictReader(f)]


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_csv(path: Path, rows: Iterable[Dict[str, Any]], fieldnames: List[str] | None = None) -> None:
    rows = list(rows)
    if fieldnames is None:
        keys = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)
        fieldnames = keys or ["message"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def redact(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if len(value) > 24 and (value.startswith("00") or value.startswith("eyJ") or value.startswith("SSWS")):
        return value[:6] + "...REDACTED..." + value[-4:]
    return value
