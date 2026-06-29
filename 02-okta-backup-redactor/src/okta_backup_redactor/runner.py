from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .config import RedactorConfig
from .jsonio import load_json, write_json
from .models import RedactionFinding, FileResult
from .redactor import redact_json
from .reporting import utc_stamp, build_result, write_markdown_report, write_json as write_report_json


def _config_summary(cfg: RedactorConfig) -> dict[str, Any]:
    return {
        "includeFiles": cfg.include_files,
        "excludeFiles": cfg.exclude_files,
        "replacement": cfg.replacement,
        "copyNonJsonFiles": cfg.copy_non_json_files,
        "redactKnownSecretKeys": cfg.redact_known_secret_keys,
        "redactAuthorizationHeaders": cfg.redact_authorization_headers,
        "redactPrivateKeyBlocks": cfg.redact_private_key_blocks,
        "redactBearerValues": cfg.redact_bearer_values,
        "redactHighEntropyValues": cfg.redact_high_entropy_values,
        "failOnFindings": cfg.fail_on_findings,
        "strictMode": cfg.strict_mode,
    }


def _iter_source_files(source: Path, cfg: RedactorConfig) -> list[Path]:
    include = set(cfg.include_files)
    exclude = set(cfg.exclude_files)
    files: list[Path] = []
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(source).as_posix()
        if include and rel not in include and path.name not in include:
            continue
        if rel in exclude or path.name in exclude:
            continue
        files.append(path)
    return files


def run_redaction(cfg: RedactorConfig, *, apply: bool = False) -> dict[str, Any]:
    source = cfg.source_backup_dir
    if not source.exists() or not source.is_dir():
        raise FileNotFoundError(f"Source backup directory not found: {source}")

    run_id = f"okta-backup-redaction-{utc_stamp()}"
    run_output_dir = cfg.output_dir / run_id
    redacted_backup_dir = run_output_dir / "redacted-backup" if apply else None
    run_output_dir.mkdir(parents=True, exist_ok=True)

    findings: list[RedactionFinding] = []
    file_results: list[FileResult] = []

    for src_file in _iter_source_files(source, cfg):
        rel = src_file.relative_to(source)
        rel_str = rel.as_posix()
        dest_file = redacted_backup_dir / rel if redacted_backup_dir else None

        if src_file.suffix.lower() != ".json":
            if apply and cfg.copy_non_json_files and dest_file:
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dest_file)
                file_results.append(FileResult(file=rel_str, status="copied_non_json", findings_count=0))
            else:
                file_results.append(FileResult(file=rel_str, status="skipped_non_json", findings_count=0))
            continue

        try:
            data = load_json(src_file)
            redacted_data, file_findings = redact_json(data, file_name=rel_str, cfg=cfg)
            findings.extend(file_findings)
            if apply and dest_file:
                write_json(dest_file, redacted_data)
                status = "redacted_written" if file_findings else "copied_json_no_findings"
            else:
                status = "planned_redaction" if file_findings else "checked_no_findings"
            file_results.append(FileResult(file=rel_str, status=status, findings_count=len(file_findings)))
        except Exception as exc:  # noqa: BLE001 - deliberate CLI error capture
            file_results.append(FileResult(file=rel_str, status="error", findings_count=0, error=str(exc)))
            if cfg.strict_mode:
                raise

    mode = "apply" if apply else "dry-run"
    result = build_result(
        run_id=run_id,
        mode=mode,
        source_backup_dir=source,
        output_dir=run_output_dir,
        redacted_backup_dir=redacted_backup_dir,
        findings=findings,
        file_results=file_results,
        config_summary=_config_summary(cfg),
    )

    write_report_json(run_output_dir / "redaction_result.json", result)
    write_markdown_report(run_output_dir / "redaction_report.md", result)

    # In apply mode, create a lightweight manifest that points to the source backup.
    if apply and redacted_backup_dir:
        write_report_json(
            run_output_dir / "redaction_manifest.json",
            {
                "utility": "okta-backup-redactor",
                "runId": run_id,
                "sourceBackupDir": str(source),
                "redactedBackupDir": str(redacted_backup_dir),
                "totalFindings": len(findings),
                "filesProcessed": len(file_results),
            },
        )

    result["reportPath"] = str(run_output_dir / "redaction_report.md")
    result["resultPath"] = str(run_output_dir / "redaction_result.json")
    if apply and redacted_backup_dir:
        result["redactedBackupDir"] = str(redacted_backup_dir)
    return result
