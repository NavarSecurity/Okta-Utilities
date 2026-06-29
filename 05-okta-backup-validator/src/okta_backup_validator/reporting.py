from __future__ import annotations

from pathlib import Path
from typing import Any

from .jsonio import write_json


def write_outputs(output_dir: Path, result: dict[str, Any]) -> dict[str, Path]:
    validation_id = str(result["validationId"])
    run_dir = output_dir / validation_id
    run_dir.mkdir(parents=True, exist_ok=False)

    result_path = run_dir / "validation_result.json"
    report_path = run_dir / "validation_report.md"
    write_json(result_path, result)
    report_path.write_text(render_markdown_report(result), encoding="utf-8")
    return {"run_dir": run_dir, "result": result_path, "report": report_path}


def render_markdown_report(result: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Okta Backup Validation Report")
    lines.append("")
    lines.append(f"- Validation ID: `{result.get('validationId')}`")
    lines.append(f"- Generated at: `{result.get('generatedAt')}`")
    lines.append(f"- Backup ID: `{result.get('backupId')}`")
    lines.append(f"- Backup directory: `{result.get('backupDir')}`")
    lines.append(f"- Org URL: `{result.get('orgUrl')}`")
    lines.append(f"- Overall status: **{result.get('overallStatus')}**")
    lines.append("")

    summary = result.get("summary", {})
    lines.append("## Summary")
    lines.append("")
    lines.append("| Result | Count |")
    lines.append("|---|---:|")
    lines.append(f"| Passed | {summary.get('passed', 0)} |")
    lines.append(f"| Warnings | {summary.get('warnings', 0)} |")
    lines.append(f"| Failures | {summary.get('failures', 0)} |")
    lines.append(f"| Total checks | {summary.get('totalChecks', 0)} |")
    lines.append("")

    checks = result.get("checks", [])
    failures = [item for item in checks if item.get("severity") == "FAIL"]
    warnings = [item for item in checks if item.get("severity") == "WARN"]
    passes = [item for item in checks if item.get("severity") == "PASS"]

    lines.append("## Failures")
    lines.append("")
    if failures:
        for item in failures:
            lines.append(format_check(item))
    else:
        lines.append("No validation failures were recorded.")
    lines.append("")

    lines.append("## Warnings")
    lines.append("")
    if warnings:
        for item in warnings:
            lines.append(format_check(item))
    else:
        lines.append("No validation warnings were recorded.")
    lines.append("")

    lines.append("## Passed Checks")
    lines.append("")
    if passes:
        for item in passes:
            lines.append(format_check(item))
    else:
        lines.append("No passed checks were recorded.")
    lines.append("")

    lines.append("## Status Meaning")
    lines.append("")
    lines.append("- `PASS`: Backup passed required validation checks.")
    lines.append("- `WARN`: Backup is structurally readable but has issues that require review, such as partial export errors.")
    lines.append("- `FAIL`: Backup should not be used for migration, restore, or evidence until failures are fixed.")
    lines.append("")
    return "\n".join(lines)


def format_check(item: dict[str, Any]) -> str:
    code = item.get("code", "UNKNOWN")
    message = item.get("message", "")
    pieces = [f"- `{code}`: {message}"]
    resource = item.get("resource")
    file_name = item.get("file")
    if resource:
        pieces.append(f"Resource: `{resource}`")
    if file_name:
        pieces.append(f"File: `{file_name}`")

    line = "  ".join(pieces)
    if code == "SENSITIVE_VALUES_FOUND":
        findings = item.get("details", {}).get("findings", []) if isinstance(item.get("details"), dict) else []
        if findings:
            details = [line, "", "  Sensitive values that should be redacted:", ""]
            details.append("  | File | Path | Key | Exact value |")
            details.append("  |---|---|---|---|")
            for finding in findings:
                details.append(
                    "  | "
                    + escape_table(str(finding.get("file", "")))
                    + " | `"
                    + escape_table(str(finding.get("path", "")))
                    + "` | `"
                    + escape_table(str(finding.get("key", "")))
                    + "` | `"
                    + escape_table(str(finding.get("value", finding.get("value_preview", ""))))
                    + "` |"
                )
            return "\n".join(details)
    return line


def escape_table(value: str) -> str:
    return value.replace("\n", " ").replace("|", "\\|")
