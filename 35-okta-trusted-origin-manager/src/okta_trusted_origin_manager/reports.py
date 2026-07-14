from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def make_run_dir(base_dir: Path, operation: str) -> Path:
    run_dir = base_dir / f"trusted-origin-{operation}-{utc_timestamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def scope_string(origin: dict[str, Any]) -> str:
    scopes = origin.get("scopes") or []
    if isinstance(scopes, list):
        values = []
        for item in scopes:
            if isinstance(item, dict):
                values.append(str(item.get("type", "")))
            else:
                values.append(str(item))
        return ";".join(sorted(value for value in values if value))
    return ""


def trusted_origin_summary_rows(origins: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in origins:
        rows.append(
            {
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "origin": item.get("origin", ""),
                "status": item.get("status", ""),
                "scopes": scope_string(item),
                "created": item.get("created", ""),
                "lastUpdated": item.get("lastUpdated", ""),
            }
        )
    return rows


def validation_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "severity": item.get("severity", ""),
            "code": item.get("code", ""),
            "name": item.get("name", ""),
            "origin": item.get("origin", ""),
            "scopes": item.get("scopes", ""),
            "message": item.get("message", ""),
        }
        for item in report.get("findings", [])
    ]


def diff_summary_rows(diff_result: dict[str, Any]) -> list[dict[str, Any]]:
    summary = diff_result.get("summary", {})
    return [{"metric": key, "value": value} for key, value in summary.items()]


def write_diff_markdown(path: Path, diff_result: dict[str, Any]) -> None:
    summary = diff_result.get("summary", {})
    lines = [
        "# Trusted Origin Drift Report",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in summary.items():
        lines.append(f"| {key} | {value} |")

    lines.extend(["", "## Missing in Target", ""])
    if diff_result.get("missingInTarget"):
        for item in diff_result["missingInTarget"]:
            lines.append(f"- `{item.get('origin')}` ({item.get('name')})")
    else:
        lines.append("None")

    lines.extend(["", "## Extra in Target", ""])
    if diff_result.get("extraInTarget"):
        for item in diff_result["extraInTarget"]:
            lines.append(f"- `{item.get('origin')}` ({item.get('name')})")
    else:
        lines.append("None")

    lines.extend(["", "## Modified", ""])
    if diff_result.get("modified"):
        for item in diff_result["modified"]:
            lines.append(f"- `{item.get('key')}`")
            for field in item.get("changedFields", []):
                lines.append(f"  - `{field.get('field')}`: source=`{field.get('source')}` target=`{field.get('target')}`")
    else:
        lines.append("None")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def manifest(operation: str, config: dict[str, Any], output_files: list[str]) -> dict[str, Any]:
    return {
        "utility": "okta-trusted-origin-manager",
        "operation": operation,
        "timestampUtc": utc_timestamp(),
        "configSummary": {
            key: value
            for key, value in config.items()
            if key.lower() not in {"oktaapitoken", "api_token", "token", "clientsecret", "client_secret"}
        },
        "outputFiles": output_files,
    }


def execution_report(operation: str, counts: dict[str, Any], warnings: list[str] | None = None, errors: list[str] | None = None, dry_run: bool | None = None) -> dict[str, Any]:
    return {
        "utility": "okta-trusted-origin-manager",
        "operation": operation,
        "dryRun": dry_run,
        "timestampUtc": utc_timestamp(),
        "counts": counts,
        "warnings": warnings or [],
        "errors": errors or [],
    }
