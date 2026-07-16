from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .redact import redact_copy


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def make_output_dir(base: Path, prefix: str) -> Path:
    output_dir = base / f"{prefix}-{utc_timestamp()}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def write_json(path: Path, data: Any, redact_sensitive: bool = False) -> None:
    safe_data = redact_copy(data) if redact_sensitive else data
    with path.open("w", encoding="utf-8") as handle:
        json.dump(safe_data, handle, indent=2, sort_keys=False)
        handle.write("\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_manifest(output_dir: Path, operation: str, files: list[str], config_path: str) -> None:
    write_json(output_dir / "manifest.json", {
        "operation": operation,
        "configPath": config_path,
        "generatedAt": utc_timestamp(),
        "files": files,
    })


def summarize_results(results: list[dict[str, Any]], status: str) -> dict[str, Any]:
    return {
        "status": status,
        "totalOperations": len(results),
        "successfulOperations": sum(1 for item in results if item.get("ok") is True),
        "failedOperations": sum(1 for item in results if item.get("ok") is False),
        "mutatingOperations": sum(1 for item in results if item.get("mutates") is True),
        "readOnlyOperations": sum(1 for item in results if item.get("mutates") is False),
        "operations": results,
    }
