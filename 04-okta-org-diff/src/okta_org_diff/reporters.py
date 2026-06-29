from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from typing import Any
import csv
import json


def make_run_dir(output_dir: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_dir / f"okta-org-diff-{stamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _change_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for resource, payload in result.get("resources", {}).items():
        for category in ["added", "removed", "changed", "duplicateKeys"]:
            for item in payload.get(category, []):
                rows.append({
                    "resource": resource,
                    "change_type": category,
                    "key": item.get("key", ""),
                    "baseline_id": item.get("baselineId", ""),
                    "comparison_id": item.get("comparisonId", ""),
                    "changed_paths": "; ".join(item.get("changedPaths", []) or []),
                    "message": item.get("message", ""),
                })
    return rows


def write_changes_csv(path: Path, result: dict[str, Any]) -> None:
    rows = _change_rows(result)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["resource", "change_type", "key", "baseline_id", "comparison_id", "changed_paths", "message"])
        writer.writeheader()
        writer.writerows(rows)


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "_None._\n"
    text = "| " + " | ".join(headers) + " |\n"
    text += "| " + " | ".join("---" for _ in headers) + " |\n"
    for row in rows:
        escaped = [str(cell).replace("\n", " ").replace("|", "\\|") for cell in row]
        text += "| " + " | ".join(escaped) + " |\n"
    return text


def write_markdown_report(path: Path, result: dict[str, Any]) -> None:
    totals = result.get("totals", {})
    lines: list[str] = []
    lines.append("# Okta Org Diff Report\n")
    lines.append(f"**Status:** `{result.get('status')}`\n")
    lines.append(f"**Generated:** `{result.get('generatedAt')}`\n")
    lines.append(f"**Baseline backup:** `{result.get('baselineBackupDir')}`\n")
    lines.append(f"**Comparison backup:** `{result.get('comparisonBackupDir')}`\n")

    lines.append("## Summary\n")
    lines.append(_md_table(
        ["Added", "Removed", "Changed", "Unchanged", "Duplicate Keys", "Warnings", "Errors"],
        [[totals.get("added", 0), totals.get("removed", 0), totals.get("changed", 0), totals.get("unchanged", 0), totals.get("duplicateKeys", 0), totals.get("warnings", 0), totals.get("errors", 0)]],
    ))

    lines.append("## Resource Summary\n")
    resource_rows = []
    for resource, payload in result.get("resources", {}).items():
        summary = payload.get("summary", {})
        resource_rows.append([
            resource,
            payload.get("baselineCount", 0),
            payload.get("comparisonCount", 0),
            summary.get("added", 0),
            summary.get("removed", 0),
            summary.get("changed", 0),
            summary.get("duplicateKeys", 0),
            summary.get("warnings", 0),
            summary.get("errors", 0),
        ])
    lines.append(_md_table(["Resource", "Baseline", "Comparison", "Added", "Removed", "Changed", "Dupes", "Warnings", "Errors"], resource_rows))

    lines.append("## Changes\n")
    change_rows = []
    for row in _change_rows(result):
        change_rows.append([
            row["resource"],
            row["change_type"],
            row["key"],
            row["baseline_id"],
            row["comparison_id"],
            row["changed_paths"],
            row["message"],
        ])
    lines.append(_md_table(["Resource", "Type", "Key", "Baseline ID", "Comparison ID", "Changed Paths", "Message"], change_rows))

    if result.get("warnings"):
        lines.append("## Warnings\n")
        lines.append(_md_table(["Resource", "Message"], [[w.get("resource"), w.get("message")] for w in result["warnings"]]))

    if result.get("errors"):
        lines.append("## Errors\n")
        lines.append(_md_table(["Resource", "Message"], [[e.get("resource"), e.get("message")] for e in result["errors"]]))

    lines.append("## Notes\n")
    lines.append("This utility compares local backup files only. It does not connect to Okta and does not change either environment. Review generated differences before using the result for migration, restore, or cutover decisions.\n")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_execution_report(path: Path, result: dict[str, Any], files: list[str]) -> None:
    lines = [
        "# Execution Report",
        "",
        f"Utility: `{result.get('utility')}`",
        f"Version: `{result.get('version')}`",
        f"Status: `{result.get('status')}`",
        f"Generated At: `{result.get('generatedAt')}`",
        f"Elapsed Seconds: `{result.get('elapsedSeconds')}`",
        "",
        "## Files Written",
        "",
    ]
    for file in files:
        lines.append(f"- `{file}`")
    lines.append("")
    lines.append("## Totals")
    lines.append("")
    for key, value in result.get("totals", {}).items():
        lines.append(f"- {key}: {value}")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_outputs(run_dir: Path, result: dict[str, Any], write_csv: bool = True, write_markdown: bool = True) -> list[str]:
    files: list[str] = []
    write_json(run_dir / "diff_result.json", result)
    files.append("diff_result.json")
    if write_csv:
        write_changes_csv(run_dir / "changes.csv", result)
        files.append("changes.csv")
    if write_markdown:
        write_markdown_report(run_dir / "diff_report.md", result)
        files.append("diff_report.md")
    write_execution_report(run_dir / "execution_report.md", result, files)
    files.append("execution_report.md")
    return files
