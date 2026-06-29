from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import RedactionFinding, FileResult


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_result(*, run_id: str, mode: str, source_backup_dir: Path, output_dir: Path, redacted_backup_dir: Path | None, findings: list[RedactionFinding], file_results: list[FileResult], config_summary: dict[str, Any]) -> dict[str, Any]:
    by_file: dict[str, int] = {}
    by_reason: dict[str, int] = {}
    for f in findings:
        by_file[f.file] = by_file.get(f.file, 0) + 1
        by_reason[f.reason] = by_reason.get(f.reason, 0) + 1

    return {
        "utility": "okta-backup-redactor",
        "version": "0.1.0",
        "runId": run_id,
        "mode": mode,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceBackupDir": str(source_backup_dir),
        "outputDir": str(output_dir),
        "redactedBackupDir": str(redacted_backup_dir) if redacted_backup_dir else None,
        "summary": {
            "filesProcessed": len(file_results),
            "filesWithFindings": len(by_file),
            "totalFindings": len(findings),
            "byFile": by_file,
            "byReason": by_reason,
        },
        "config": config_summary,
        "files": [r.to_dict() for r in file_results],
        "findings": [f.to_dict() for f in findings],
    }


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def write_markdown_report(path: Path, result: dict[str, Any]) -> None:
    lines: list[str] = []
    summary = result["summary"]
    lines.append("# Okta Backup Redaction Report")
    lines.append("")
    lines.append(f"**Run ID:** `{result['runId']}`")
    lines.append(f"**Mode:** `{result['mode']}`")
    lines.append(f"**Source backup:** `{result['sourceBackupDir']}`")
    if result.get("redactedBackupDir"):
        lines.append(f"**Redacted backup:** `{result['redactedBackupDir']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Files processed: `{summary['filesProcessed']}`")
    lines.append(f"- Files with findings: `{summary['filesWithFindings']}`")
    lines.append(f"- Values redacted / planned for redaction: `{summary['totalFindings']}`")
    lines.append("")

    if summary["byFile"]:
        lines.append("## Findings by File")
        lines.append("")
        lines.append("| File | Findings |")
        lines.append("|---|---:|")
        for file, count in sorted(summary["byFile"].items()):
            lines.append(f"| `{file}` | {count} |")
        lines.append("")

    if result["findings"]:
        lines.append("## Redaction Findings")
        lines.append("")
        lines.append("| File | JSON Path | Key | Reason | Value Preview |")
        lines.append("|---|---|---|---|---|")
        for f in result["findings"]:
            preview = str(f.get("value_preview", "")).replace("|", "\\|")
            lines.append(
                f"| `{f['file']}` | `{f['path']}` | `{f.get('key') or ''}` | {f['reason']} | `{preview}` |"
            )
        lines.append("")
    else:
        lines.append("## Findings")
        lines.append("")
        lines.append("No sensitive values were found by the configured redaction rules.")
        lines.append("")

    lines.append("## Notes")
    lines.append("")
    if result["mode"] == "dry-run":
        lines.append("Dry-run mode did not write a redacted backup copy. Re-run with `--apply` to write redacted files.")
    else:
        lines.append("Apply mode wrote a redacted copy and did not modify the source backup folder.")
    lines.append("Review generated reports before committing or sharing any backup output.")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
