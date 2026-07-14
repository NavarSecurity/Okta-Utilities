from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import RuntimeConfig, require_okta_settings
from .diff import compare_trusted_origins
from .normalize import extract_trusted_origins, key_for_origin, scope_types, to_okta_payload
from .okta_client import OktaClient
from .reports import (
    diff_summary_rows,
    execution_report,
    make_run_dir,
    manifest,
    trusted_origin_summary_rows,
    validation_rows,
    write_csv,
    write_diff_markdown,
    write_json,
)
from .validate import validate_trusted_origins


def _read_json_file(path_value: str | None, label: str) -> Any:
    if not path_value:
        raise ValueError(f"{label} is required")
    path = Path(path_value)
    if not path.exists():
        raise ValueError(f"{label} not found: {path}")
    if not path.is_file():
        raise ValueError(f"{label} must point to a JSON file, not a folder: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {label} {path}: {exc}") from exc


def _client(config: RuntimeConfig) -> OktaClient:
    require_okta_settings(config)
    return OktaClient(
        org_url=config.okta_org_url or "",
        api_token=config.okta_api_token or "",
        timeout_seconds=config.timeout_seconds,
        max_retries=config.max_retries,
    )


def export_operation(config: RuntimeConfig) -> Path:
    run_dir = make_run_dir(config.output_directory, "export")
    client = _client(config)
    all_origins = client.list_trusted_origins()

    include_inactive = bool(config.raw.get("includeInactiveOrigins", True))
    origins = all_origins if include_inactive else [item for item in all_origins if item.get("status") == "ACTIVE"]
    payload = {"trustedOrigins": origins}
    validation_report = validate_trusted_origins(payload, config.raw)

    files: list[str] = []
    write_json(run_dir / "trusted_origins_full.json", payload)
    files.append("trusted_origins_full.json")

    write_csv(
        run_dir / "trusted_origins_summary.csv",
        trusted_origin_summary_rows(origins),
        ["id", "name", "origin", "status", "scopes", "created", "lastUpdated"],
    )
    files.append("trusted_origins_summary.csv")

    by_scope_dir = run_dir / "trusted_origins_by_scope"
    by_scope_dir.mkdir(exist_ok=True)
    for scope in ["CORS", "REDIRECT", "IFRAME_EMBED"]:
        scoped = [item for item in origins if scope in scope_types(item)]
        write_json(by_scope_dir / f"{scope.lower()}.json", {"trustedOrigins": scoped})
    files.append("trusted_origins_by_scope/")

    write_json(run_dir / "validation_report.json", validation_report)
    files.append("validation_report.json")

    report = execution_report(
        "export",
        {
            "totalTrustedOriginsReturned": len(all_origins),
            "totalTrustedOriginsExported": len(origins),
            "validationErrors": validation_report["errorCount"],
            "validationWarnings": validation_report["warningCount"],
        },
        warnings=[item["message"] for item in validation_report.get("findings", []) if item.get("severity") == "WARNING"],
    )
    write_json(run_dir / "execution_report.json", report)
    files.append("execution_report.json")
    write_json(run_dir / "manifest.json", manifest("export", config.raw, files))
    return run_dir


def compare_operation(config: RuntimeConfig) -> Path:
    run_dir = make_run_dir(config.output_directory, "compare")
    source_file = config.raw.get("sourceFile") or config.raw.get("compare", {}).get("sourceFile")
    target_file = config.raw.get("targetFile") or config.raw.get("compare", {}).get("targetFile")
    match_by = config.raw.get("matchStrategy") or config.raw.get("matchBy") or config.raw.get("compare", {}).get("matchBy") or "origin"
    include_status = bool(config.raw.get("includeStatusInCompare", True))

    source_payload = _read_json_file(source_file, "sourceFile")
    target_payload = _read_json_file(target_file, "targetFile")
    diff_result = compare_trusted_origins(source_payload, target_payload, match_by=match_by, include_status=include_status)

    files: list[str] = []
    write_json(run_dir / "trusted_origin_diff_details.json", diff_result)
    files.append("trusted_origin_diff_details.json")
    write_csv(run_dir / "trusted_origin_diff_summary.csv", diff_summary_rows(diff_result), ["metric", "value"])
    files.append("trusted_origin_diff_summary.csv")
    write_diff_markdown(run_dir / "trusted_origin_diff_report.md", diff_result)
    files.append("trusted_origin_diff_report.md")

    report = execution_report("compare", diff_result.get("summary", {}))
    write_json(run_dir / "execution_report.json", report)
    files.append("execution_report.json")
    write_json(run_dir / "manifest.json", manifest("compare", config.raw, files))
    return run_dir


def validate_operation(config: RuntimeConfig) -> Path:
    run_dir = make_run_dir(config.output_directory, "validate")
    input_file = config.raw.get("inputFile") or config.raw.get("validate", {}).get("inputFile")
    payload = _read_json_file(input_file, "inputFile")
    validation_report = validate_trusted_origins(payload, config.raw)

    files: list[str] = []
    write_json(run_dir / "validation_report.json", validation_report)
    files.append("validation_report.json")
    write_csv(
        run_dir / "trusted_origins_validation.csv",
        validation_rows(validation_report),
        ["severity", "code", "name", "origin", "scopes", "message"],
    )
    files.append("trusted_origins_validation.csv")

    report = execution_report(
        "validate",
        {
            "totalTrustedOrigins": validation_report["totalOrigins"],
            "validationErrors": validation_report["errorCount"],
            "validationWarnings": validation_report["warningCount"],
        },
        warnings=[item["message"] for item in validation_report.get("findings", []) if item.get("severity") == "WARNING"],
        errors=[item["message"] for item in validation_report.get("findings", []) if item.get("severity") == "ERROR"],
    )
    write_json(run_dir / "execution_report.json", report)
    files.append("execution_report.json")
    write_json(run_dir / "manifest.json", manifest("validate", config.raw, files))
    return run_dir


def import_operation(config: RuntimeConfig, apply: bool) -> Path:
    run_dir = make_run_dir(config.output_directory, "import")
    input_file = config.raw.get("inputFile") or config.raw.get("import", {}).get("inputFile")
    payload = _read_json_file(input_file, "inputFile")
    desired = extract_trusted_origins(payload)

    validation_report = validate_trusted_origins(payload, config.raw)
    if config.raw.get("validateBeforeImport", True) and validation_report["errorCount"] > 0:
        write_json(run_dir / "validation_report.json", validation_report)
        report = execution_report(
            "import",
            {"planned": 0, "created": 0, "replaced": 0, "skipped": 0, "failed": 0},
            errors=["Validation failed. Resolve validation errors before import."],
            dry_run=not apply,
        )
        write_json(run_dir / "execution_report.json", report)
        write_json(run_dir / "manifest.json", manifest("import", config.raw, ["validation_report.json", "execution_report.json"]))
        return run_dir

    client = _client(config)
    existing = client.list_trusted_origins()
    match_by = config.raw.get("matchBy") or "origin"
    on_existing = (config.raw.get("onExisting") or "skip").lower()
    if on_existing not in {"skip", "replace"}:
        raise ValueError("onExisting must be skip or replace")

    existing_map = {key_for_origin(item, match_by): item for item in existing if key_for_origin(item, match_by)}
    planned: list[dict[str, Any]] = []
    applied: list[dict[str, Any]] = []
    rollback: list[dict[str, Any]] = []
    errors: list[str] = []

    for item in desired:
        key = key_for_origin(item, match_by)
        if not key:
            planned.append({"action": "skip", "reason": "No match key", "origin": item})
            continue
        existing_item = existing_map.get(key)
        okta_payload = to_okta_payload(item)
        if existing_item:
            if on_existing == "skip":
                planned.append({"action": "skip", "reason": "Existing trusted origin found", "existingId": existing_item.get("id"), "payload": okta_payload})
                continue
            planned.append({"action": "replace", "existingId": existing_item.get("id"), "payload": okta_payload})
            if apply:
                try:
                    result = client.replace_trusted_origin(str(existing_item.get("id")), okta_payload)
                    applied.append({"action": "replace", "id": result.get("id"), "name": result.get("name"), "origin": result.get("origin")})
                    rollback.append({"action": "replace", "id": existing_item.get("id"), "payload": to_okta_payload(existing_item)})
                except Exception as exc:  # noqa: BLE001 - report and continue
                    errors.append(f"Failed to replace {okta_payload.get('origin')}: {exc}")
        else:
            planned.append({"action": "create", "payload": okta_payload})
            if apply:
                try:
                    result = client.create_trusted_origin(okta_payload)
                    applied.append({"action": "create", "id": result.get("id"), "name": result.get("name"), "origin": result.get("origin")})
                    rollback.append({"action": "delete", "id": result.get("id"), "name": result.get("name"), "origin": result.get("origin")})
                except Exception as exc:  # noqa: BLE001 - report and continue
                    errors.append(f"Failed to create {okta_payload.get('origin')}: {exc}")

    files: list[str] = []
    write_json(run_dir / "planned_changes.json", {"changes": planned})
    files.append("planned_changes.json")
    write_json(run_dir / "applied_changes.json", {"changes": applied})
    files.append("applied_changes.json")
    write_json(run_dir / "rollback_actions.json", {"actions": rollback})
    files.append("rollback_actions.json")
    write_json(run_dir / "validation_report.json", validation_report)
    files.append("validation_report.json")

    counts = {
        "inputTrustedOrigins": len(desired),
        "planned": len(planned),
        "created": len([item for item in applied if item.get("action") == "create"]),
        "replaced": len([item for item in applied if item.get("action") == "replace"]),
        "skipped": len([item for item in planned if item.get("action") == "skip"]),
        "failed": len(errors),
        "validationErrors": validation_report["errorCount"],
        "validationWarnings": validation_report["warningCount"],
    }
    report = execution_report(
        "import",
        counts,
        warnings=[item["message"] for item in validation_report.get("findings", []) if item.get("severity") == "WARNING"],
        errors=errors,
        dry_run=not apply,
    )
    write_json(run_dir / "execution_report.json", report)
    files.append("execution_report.json")
    write_json(run_dir / "manifest.json", manifest("import", config.raw, files))
    return run_dir
