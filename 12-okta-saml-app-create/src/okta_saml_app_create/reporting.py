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
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_mapping_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["label", "action", "targetAppId", "targetAppUrl", "message"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_report(path: Path, result: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append(f"# Okta SAML App Create Report")
    lines.append("")
    lines.append(f"Run ID: `{result.get('runId')}`")
    lines.append(f"Mode: `{result.get('mode')}`")
    lines.append(f"Target org: `{result.get('targetOrgUrl')}`")
    lines.append(f"Overall status: `{result.get('status')}`")
    lines.append("")
    lines.append("## Requested app")
    app = result.get("app", {})
    lines.append(f"- Label: `{app.get('label', '')}`")
    lines.append(f"- SSO ACS URL: `{app.get('ssoAcsUrl', '')}`")
    lines.append(f"- Audience: `{app.get('audience', '')}`")
    lines.append("")
    counts = result.get("counts", {})
    lines.append("## Counts")
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
                lines.append(f"- `{err.get('statusCode', '')}` {err.get('message', '')} ({err.get('url', '')})")
            else:
                lines.append(f"- {err}")
        lines.append("")
    request_summary = result.get("requestSummary", {})
    if request_summary:
        lines.append("## Request summary")
        lines.append(f"- Total requests: {request_summary.get('totalRequests', 0)}")
        lines.append(f"- By status: `{request_summary.get('byStatus', {})}`")
        lines.append("")
    lines.append("## Output files")
    for output_file in result.get("outputFiles", []):
        lines.append(f"- `{output_file}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
