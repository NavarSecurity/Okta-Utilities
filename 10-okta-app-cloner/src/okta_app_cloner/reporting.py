from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .config import AppClonerConfig
from .loader import CloneResult
from .planner import ClonePlan


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=False), encoding="utf-8")


def make_run_dir(output_dir: Path) -> Path:
    run_dir = output_dir / f"okta-app-cloner-{timestamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_outputs(run_dir: Path, config: AppClonerConfig, plan: ClonePlan, result: CloneResult, apply: bool) -> dict[str, str]:
    plan_path = run_dir / "clone_plan.json"
    result_path = run_dir / "clone_result.json"
    rollback_path = run_dir / "rollback_plan.json"
    mapping_path = run_dir / "app_mapping.csv"
    report_path = run_dir / "execution_report.md"

    write_json(plan_path, plan.to_dict(include_payload=True))
    write_json(
        result_path,
        {
            "utility": "okta-app-cloner",
            "version": __version__,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "mode": "apply" if apply else "dry-run",
            "sourceBackupDir": str(config.source_backup_dir),
            "targetOrgUrl": config.target_org_url,
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
    _write_mapping_csv(mapping_path, result)
    report_path.write_text(_report_markdown(config, plan, result, apply), encoding="utf-8")
    return {
        "plan": str(plan_path),
        "result": str(result_path),
        "rollback": str(rollback_path),
        "mapping": str(mapping_path),
        "report": str(report_path),
    }


def _write_mapping_csv(path: Path, result: CloneResult) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["label", "source_id", "target_id", "status", "sign_on_mode"])
        writer.writeheader()
        for op in result.operations:
            writer.writerow({
                "label": op.get("label", ""),
                "source_id": op.get("sourceId", ""),
                "target_id": op.get("targetId", ""),
                "status": op.get("status", ""),
                "sign_on_mode": op.get("signOnMode", ""),
            })


def _report_markdown(config: AppClonerConfig, plan: ClonePlan, result: CloneResult, apply: bool) -> str:
    lines: list[str] = []
    lines.append("# Okta App Cloner Execution Report")
    lines.append("")
    lines.append("- Utility: `okta-app-cloner`")
    lines.append(f"- Version: `{__version__}`")
    lines.append(f"- Mode: `{'apply' if apply else 'dry-run'}`")
    lines.append(f"- Generated At: `{datetime.now(timezone.utc).isoformat()}`")
    lines.append(f"- Source Backup Directory: `{config.source_backup_dir}`")
    lines.append(f"- Target Org URL: `{config.target_org_url}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Planned clone operations: `{len(plan.operations)}`")
    lines.append(f"- Executed / would execute: `{len(result.operations)}`")
    lines.append(f"- Skipped: `{len(result.skipped)}`")
    lines.append(f"- Errors: `{len(result.errors)}`")
    lines.append(f"- Rollback actions generated: `{len(result.rollback)}`")
    lines.append("")
    lines.append("## Operations")
    lines.append("")
    if result.operations:
        lines.append("| App Label | Source ID | Target ID | Status | Sign-on Mode |")
        lines.append("|---|---|---|---|---|")
        for op in result.operations:
            lines.append(f"| {op.get('label', '')} | {op.get('sourceId', '')} | {op.get('targetId', '') or ''} | {op.get('status', '')} | {op.get('signOnMode', '')} |")
    else:
        lines.append("No operations were executed or planned for execution.")
    lines.append("")
    lines.append("## Skipped")
    lines.append("")
    if result.skipped:
        lines.append("| App Label | Source ID | Reason |")
        lines.append("|---|---|---|")
        for item in result.skipped:
            lines.append(f"| {item.get('label', '')} | {item.get('sourceId', '')} | {item.get('reason', '')} |")
    else:
        lines.append("No skipped items.")
    lines.append("")
    lines.append("## Errors")
    lines.append("")
    if result.errors:
        lines.append("| App Label | Stage/Method | Status Code | Message |")
        lines.append("|---|---|---:|---|")
        for err in result.errors:
            lines.append(f"| {err.get('label', '')} | {err.get('stage') or err.get('method', '')} | {err.get('statusCode', '')} | {err.get('message', '')} |")
    else:
        lines.append("No errors recorded.")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- App assignments are not cloned by this version.")
    lines.append("- Provisioning settings are omitted by default and should be reviewed manually.")
    lines.append("- Client secrets and other source-org credentials are not cloned. Target app secrets should be rotated/generated in the target org.")
    lines.append("- Review `rollback_plan.json` if apply mode created any objects.")
    lines.append("")
    lines.append("## Request Summary")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(result.request_summary, indent=2))
    lines.append("```")
    return "\n".join(lines) + "\n"
