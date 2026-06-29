from __future__ import annotations

from typing import Any


def build_inventory_report(inv: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# Okta Org Inventory Report")
    lines.append("")
    lines.append(f"Run ID: `{inv.get('runId')}`")
    lines.append(f"Source backup: `{inv.get('sourceBackupDir')}`")
    manifest = inv.get("manifest") or {}
    if manifest:
        lines.append(f"Backup ID: `{manifest.get('backupId')}`")
        lines.append(f"Org URL: `{manifest.get('orgUrl')}`")
        lines.append(f"Generated at: `{manifest.get('generatedAt')}`")
        lines.append(f"Redaction enabled: `{manifest.get('redactionEnabled')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"Total records inventoried: **{inv.get('summary', {}).get('totalRecords', 0)}**")
    lines.append("")
    lines.append("| Resource | Count | Status summary | Type summary |")
    lines.append("|---|---:|---|---|")
    for resource, summary in sorted((inv.get("summary", {}).get("resources") or {}).items()):
        lines.append(f"| `{resource}` | {summary.get('count', 0)} | {_fmt_counts(summary.get('byStatus', {}))} | {_fmt_counts(summary.get('byType', {}))} |")
    lines.append("")

    if inv.get("warnings"):
        lines.append("## Warnings")
        lines.append("")
        for w in inv["warnings"]:
            lines.append(f"- `{w.get('code')}`: {w.get('message')}")
        lines.append("")

    if inv.get("errors"):
        lines.append("## Errors")
        lines.append("")
        for e in inv["errors"]:
            parts = [f"`{e.get('code')}`: {e.get('message')}"]
            if e.get("resource"):
                parts.append(f"Resource: `{e.get('resource')}`")
            if e.get("file"):
                parts.append(f"File: `{e.get('file')}`")
            lines.append("- " + "  ".join(parts))
        lines.append("")

    lines.append("## Resource previews")
    lines.append("")
    for resource, details in sorted((inv.get("resources") or {}).items()):
        rows = details.get("rows", [])
        lines.append(f"### `{resource}`")
        lines.append("")
        lines.append(f"Count: **{details.get('count', 0)}**")
        if rows:
            fieldnames = details.get("fieldnames", [])[:6]
            lines.append("")
            lines.append("| " + " | ".join(fieldnames) + " |")
            lines.append("|" + "|".join("---" for _ in fieldnames) + "|")
            for row in rows[:10]:
                lines.append("| " + " | ".join(_cell(row.get(f, "")) for f in fieldnames) + " |")
            if len(rows) > 10:
                lines.append(f"\n_Showing first 10 of {len(rows)} records._")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_execution_report(inv: dict[str, Any]) -> str:
    status = "FAILED" if inv.get("errors") else "COMPLETED_WITH_WARNINGS" if inv.get("warnings") else "COMPLETED"
    lines = [
        "# Inventory Execution Report",
        "",
        f"Status: **{status}**",
        f"Run ID: `{inv.get('runId')}`",
        f"Source backup: `{inv.get('sourceBackupDir')}`",
        f"Output directory: `{inv.get('outputDir')}`",
        f"Resources requested: `{', '.join(inv.get('config', {}).get('include', []))}`",
        f"Total records inventoried: **{inv.get('summary', {}).get('totalRecords', 0)}**",
        f"Warnings: **{len(inv.get('warnings', []))}**",
        f"Errors: **{len(inv.get('errors', []))}**",
        "",
        "## Output files",
        "",
    ]
    for path in inv.get("outputFiles", []):
        lines.append(f"- `{path}`")
    return "\n".join(lines).rstrip() + "\n"


def _fmt_counts(counts: dict[str, Any]) -> str:
    if not counts:
        return ""
    return ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))


def _cell(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("|", "\\|").replace("\n", " ")
    return text[:120]
