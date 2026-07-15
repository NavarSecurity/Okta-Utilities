from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def make_output_dir(base_dir: str | Path, dry_run: bool = False) -> Path:
    prefix = "profile-mapping-export-dry-run" if dry_run else "profile-mapping-export"
    output_dir = Path(base_dir) / f"{prefix}-{utc_timestamp()}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def write_json(path: str | Path, data: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=False)
        handle.write("\n")


def write_csv(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        field_set: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in field_set:
                    field_set.append(key)
        fieldnames = field_set
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def manifest(operation: str, config_path: str, files: list[str], dry_run: bool) -> dict[str, Any]:
    return {
        "utility": "okta-profile-mapping-exporter",
        "operation": operation,
        "dryRun": dry_run,
        "timestampUtc": datetime.now(timezone.utc).isoformat(),
        "configPath": config_path,
        "files": files,
    }
