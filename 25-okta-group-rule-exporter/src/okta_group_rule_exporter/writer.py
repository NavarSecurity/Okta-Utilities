from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown_summary(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Okta Group Rule Export Summary",
        "",
        f"Mode: {result.get('mode')}",
        f"Target org: {result.get('targetOrgUrl')}",
        f"Rules returned by Okta: {result.get('rulesReturned')}",
        f"Rules exported after filters: {result.get('rulesExported')}",
        f"Errors: {len(result.get('errors', []))}",
        "",
        "## Status counts",
        "",
    ]
    counts = result.get("statusCounts", {})
    if counts:
        for status, count in sorted(counts.items()):
            lines.append(f"- {status}: {count}")
    else:
        lines.append("- None")
    lines.extend([
        "",
        "## Output files",
        "",
    ])
    for file_name in result.get("outputFiles", []):
        lines.append(f"- {file_name}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_execution_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Execution Report",
        "",
        f"Utility: okta-group-rule-exporter",
        f"Version: {result.get('version')}",
        f"Mode: {result.get('mode')}",
        f"Started: {result.get('startedAt')}",
        f"Finished: {result.get('finishedAt')}",
        f"Target org: {result.get('targetOrgUrl')}",
        "",
        "## Counts",
        "",
        f"- Rules returned by Okta: {result.get('rulesReturned')}",
        f"- Rules exported after filters: {result.get('rulesExported')}",
        f"- Request count: {len(result.get('requests', []))}",
        f"- Error count: {len(result.get('errors', []))}",
        "",
        "## Files",
        "",
    ]
    for file_name in result.get("outputFiles", []):
        lines.append(f"- {file_name}")
    if result.get("errors"):
        lines.extend(["", "## Errors", ""])
        for error in result["errors"]:
            lines.append(f"- {error}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
