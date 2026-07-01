from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import datetime, timezone
import csv
import json


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_markdown_summary(path: Path, result: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# Okta App Assignment Export Summary")
    lines.append("")
    lines.append(f"Run ID: `{result.get('runId')}`")
    lines.append(f"Mode: `{result.get('mode')}`")
    lines.append(f"Target org: `{result.get('targetOrgUrl')}`")
    lines.append(f"Overall status: `{result.get('status')}`")
    lines.append("")
    counts = result.get("counts", {})
    lines.append("## Counts")
    for key in sorted(counts):
        lines.append(f"- {key}: {counts[key]}")
    lines.append("")
    selection = result.get("selection", {})
    lines.append("## Selection")
    lines.append(f"- Mode: `{selection.get('mode', '')}`")
    lines.append(f"- Labels: `{selection.get('appLabels', [])}`")
    lines.append(f"- IDs: `{selection.get('appIds', [])}`")
    lines.append(f"- Statuses: `{selection.get('statuses', [])}`")
    lines.append(f"- Sign-on modes: `{selection.get('signOnModes', [])}`")
    lines.append("")
    apps = result.get("apps", [])
    if apps:
        lines.append("## Exported apps")
        lines.append("| App label | App ID | Sign-on mode | Status | Users | Groups | Errors |")
        lines.append("|---|---|---:|---:|---:|---:|---:|")
        for app in apps:
            lines.append(
                f"| {app.get('appLabel', '')} | `{app.get('appId', '')}` | {app.get('signOnMode', '')} | {app.get('status', '')} | {app.get('assignedUserCount', 0)} | {app.get('assignedGroupCount', 0)} | {app.get('errorCount', 0)} |"
            )
        lines.append("")
    if result.get("warnings"):
        lines.append("## Warnings")
        for warning in result["warnings"]:
            lines.append(f"- {warning}")
        lines.append("")
    if result.get("errors"):
        lines.append("## Errors")
        for err in result["errors"]:
            if isinstance(err, dict):
                lines.append(f"- `{err.get('statusCode', '')}` {err.get('message', '')} ({err.get('resource', '')})")
            else:
                lines.append(f"- {err}")
        lines.append("")
    lines.append("## Output files")
    for output_file in result.get("outputFiles", []):
        lines.append(f"- `{output_file}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_execution_report(path: Path, result: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# Okta App Assignment Exporter Execution Report")
    lines.append("")
    lines.append(f"Run ID: `{result.get('runId')}`")
    lines.append(f"Mode: `{result.get('mode')}`")
    lines.append(f"Target org: `{result.get('targetOrgUrl')}`")
    lines.append(f"Status: `{result.get('status')}`")
    lines.append("")
    lines.append("## Request summary")
    summary = result.get("requestSummary", {})
    lines.append(f"- Total requests: {summary.get('totalRequests', 0)}")
    lines.append(f"- By status: `{summary.get('byStatus', {})}`")
    lines.append(f"- Total elapsed seconds: {summary.get('totalElapsedSeconds', 0)}")
    lines.append("")
    lines.append("## Counts")
    counts = result.get("counts", {})
    for key in sorted(counts):
        lines.append(f"- {key}: {counts[key]}")
    lines.append("")
    if result.get("warnings"):
        lines.append("## Warnings")
        for warning in result["warnings"]:
            lines.append(f"- {warning}")
        lines.append("")
    if result.get("errors"):
        lines.append("## Errors")
        for err in result["errors"]:
            if isinstance(err, dict):
                lines.append(f"- `{err.get('statusCode', '')}` {err.get('message', '')} | Resource: `{err.get('resource', '')}` | URL: `{err.get('url', '')}`")
            else:
                lines.append(f"- {err}")
        lines.append("")
    lines.append("## Output files")
    for output_file in result.get("outputFiles", []):
        lines.append(f"- `{output_file}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
