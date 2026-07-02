from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


def write_execution_report(path: Path, result: Dict[str, Any]) -> None:
    summary = result.get("summary", {})
    request_summary = result.get("requestSummary", {})
    errors = result.get("errors", [])
    lines: List[str] = []
    lines.append("# Okta API Authorization Server Builder Execution Report")
    lines.append("")
    lines.append(f"Run ID: `{result.get('runId', '')}`")
    lines.append(f"Mode: `{result.get('mode', '')}`")
    lines.append(f"Target org: `{result.get('targetOrgUrl', '')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|---|---:|")
    for key in [
        "authorizationServersPlanned",
        "authorizationServersCreated",
        "authorizationServersExisting",
        "scopesCreated",
        "scopesExisting",
        "claimsCreated",
        "claimsExisting",
        "policiesCreated",
        "policiesExisting",
        "rulesCreated",
        "rulesExisting",
        "skipped",
        "errors",
    ]:
        lines.append(f"| {key} | {summary.get(key, 0)} |")
    lines.append("")
    if request_summary:
        lines.append("## Request Summary")
        lines.append("")
        lines.append(f"Total requests: `{request_summary.get('totalRequests', 0)}`")
        lines.append("")
        if request_summary.get("byStatus"):
            lines.append("| HTTP Status | Count |")
            lines.append("|---|---:|")
            for status, count in sorted(request_summary.get("byStatus", {}).items()):
                lines.append(f"| {status} | {count} |")
            lines.append("")
    if errors:
        lines.append("## Errors")
        lines.append("")
        for error in errors:
            lines.append(f"- `{error.get('itemType', 'unknown')}` `{error.get('name', '')}`: {error.get('message', '')}")
        lines.append("")
    lines.append("## Output Files")
    lines.append("")
    for output in result.get("outputFiles", []):
        lines.append(f"- `{output}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
