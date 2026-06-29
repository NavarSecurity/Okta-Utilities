from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .config import RestoreConfig
from .loader import RestoreResult
from .planner import RestorePlan


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=False), encoding="utf-8")


def make_run_dir(output_dir: Path) -> Path:
    run_dir = output_dir / f"okta-selective-restore-{timestamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_outputs(run_dir: Path, config: RestoreConfig, plan: RestorePlan, result: RestoreResult, apply: bool) -> dict[str, str]:
    plan_path = run_dir / "restore_plan.json"
    result_path = run_dir / "restore_result.json"
    rollback_path = run_dir / "rollback_plan.json"
    report_path = run_dir / "execution_report.md"

    write_json(plan_path, plan.to_dict(include_payload=True))
    write_json(
        result_path,
        {
            "utility": "okta-selective-restore",
            "version": __version__,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "mode": "apply" if apply else "dry-run",
            "targetOrgUrl": config.target_org_url,
            "sourceBackupDir": str(config.source_backup_dir),
            "include": config.include,
            "operations": result.operations,
            "skipped": result.skipped,
            "errors": result.errors,
            "requestSummary": result.request_summary,
            "counts": {
                "planned": len(plan.operations),
                "executedOrWouldExecute": len(result.operations),
                "skipped": len(result.skipped),
                "errors": len(result.errors),
                "rollbackActions": len(result.rollback),
            },
        },
    )
    write_json(rollback_path, {"rollback": result.rollback})
    report_path.write_text(_report_markdown(config, plan, result, apply), encoding="utf-8")
    return {
        "plan": str(plan_path),
        "result": str(result_path),
        "rollback": str(rollback_path),
        "report": str(report_path),
    }


def _report_markdown(config: RestoreConfig, plan: RestorePlan, result: RestoreResult, apply: bool) -> str:
    lines: list[str] = []
    lines.append("# Okta Selective Restore Execution Report")
    lines.append("")
    lines.append(f"- Utility: `okta-selective-restore`")
    lines.append(f"- Version: `0.1.0`")
    lines.append(f"- Mode: `{'apply' if apply else 'dry-run'}`")
    lines.append(f"- Generated At: `{datetime.now(timezone.utc).isoformat()}`")
    lines.append(f"- Source Backup Directory: `{config.source_backup_dir}`")
    lines.append(f"- Target Org URL: `{config.target_org_url}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Planned operations: `{len(plan.operations)}`")
    lines.append(f"- Executed / would execute: `{len(result.operations)}`")
    lines.append(f"- Skipped: `{len(result.skipped)}`")
    lines.append(f"- Errors: `{len(result.errors)}`")
    lines.append(f"- Rollback actions generated: `{len(result.rollback)}`")
    lines.append("")
    lines.append("## Resources Requested")
    lines.append("")
    for resource in config.include:
        lines.append(f"- `{resource}`")
    lines.append("")
    lines.append("## Operations")
    lines.append("")
    if result.operations:
        lines.append("| Resource | Name | Status | Target ID |")
        lines.append("|---|---|---|---|")
        for op in result.operations:
            lines.append(f"| {op.get('resource')} | {op.get('displayName')} | {op.get('status')} | {op.get('targetId') or ''} |")
    else:
        lines.append("No operations were executed or planned for execution.")
    lines.append("")
    lines.append("## Skipped")
    lines.append("")
    if result.skipped:
        lines.append("| Resource | Name | Reason |")
        lines.append("|---|---|---|")
        for item in result.skipped:
            lines.append(f"| {item.get('resource')} | {item.get('displayName', '')} | {item.get('reason', '')} |")
    else:
        lines.append("No skipped items.")
    lines.append("")
    lines.append("## Errors")
    lines.append("")
    if result.errors:
        lines.append("| Resource | Name | Status Code | Message |")
        lines.append("|---|---|---:|---|")
        for err in result.errors:
            lines.append(f"| {err.get('resource')} | {err.get('displayName', '')} | {err.get('statusCode', '')} | {err.get('message', '')} |")
    else:
        lines.append("No errors recorded.")
    lines.append("")
    lines.append("## Request Summary")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(result.request_summary, indent=2))
    lines.append("```")
    return "\n".join(lines) + "\n"
