from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import get_okta_env
from .normalize import group_by_type, mapping_properties, mapping_summary, sources_targets
from .okta_client import OktaApiError, OktaClient
from .redact import redact_value
from .reports import manifest, make_output_dir, write_csv, write_json


def run_export(config: dict[str, Any], config_path: str, dry_run: bool = False) -> Path:
    output_dir = make_output_dir(config.get("outputDirectory", "output"), dry_run=dry_run)
    files: list[str] = []

    if dry_run:
        report = {
            "status": "DRY_RUN_SUCCESS",
            "dryRun": True,
            "message": "Configuration validated. No Okta API calls were made.",
            "configuredOutputDirectory": config.get("outputDirectory"),
            "includeMappingDetails": config.get("includeMappingDetails"),
            "filters": config.get("filters", {}),
            "warnings": [],
            "errors": [],
        }
        write_json(output_dir / "execution_report.json", report)
        files.append("execution_report.json")
        write_json(output_dir / "manifest.json", manifest("export", config_path, files, dry_run=True))
        return output_dir

    org_url, token = get_okta_env()
    retry = config.get("retry", {})
    client = OktaClient(
        org_url=org_url,
        api_token=token,
        timeout_seconds=int(config.get("timeoutSeconds", 30)),
        max_attempts=int(retry.get("maxAttempts", 3)),
        backoff_seconds=float(retry.get("backoffSeconds", 1)),
    )

    filters = config.get("filters", {}) or {}
    source_id = filters.get("sourceId") or None
    target_id = filters.get("targetId") or None
    warnings: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    summaries = client.list_profile_mappings(
        limit=int(config.get("limit", 200)),
        source_id=source_id,
        target_id=target_id,
    )

    mappings: list[dict[str, Any]] = []
    if config.get("includeMappingDetails", True):
        for summary in summaries:
            mapping_id = summary.get("id")
            if not mapping_id:
                warnings.append({"message": "Profile mapping summary did not include an id", "summary": summary})
                mappings.append(summary)
                continue
            try:
                mappings.append(client.get_profile_mapping(str(mapping_id)))
            except OktaApiError as exc:
                warnings.append(
                    {
                        "mappingId": mapping_id,
                        "message": "Failed to retrieve mapping detail. Using summary response instead.",
                        "statusCode": exc.status_code,
                        "error": str(exc),
                    }
                )
                mappings.append(summary)
    else:
        mappings = summaries

    export_data = redact_value(mappings) if config.get("redactSensitiveValues", True) else mappings
    write_json(output_dir / "mappings_full.json", export_data)
    files.append("mappings_full.json")

    summary_rows = [mapping_summary(mapping) for mapping in export_data]
    property_rows: list[dict[str, Any]] = []
    for mapping in export_data:
        property_rows.extend(mapping_properties(mapping))
    source_target_rows = sources_targets(export_data)

    write_csv(output_dir / "profile_mappings_summary.csv", summary_rows)
    files.append("profile_mappings_summary.csv")
    write_csv(output_dir / "profile_mapping_properties.csv", property_rows)
    files.append("profile_mapping_properties.csv")
    write_csv(output_dir / "mapping_sources_targets.csv", source_target_rows)
    files.append("mapping_sources_targets.csv")

    source_dir = output_dir / "mappings_by_source_type"
    target_dir = output_dir / "mappings_by_target_type"
    for type_name, rows in group_by_type(export_data, "source").items():
        file_name = safe_file_name(type_name) + ".json"
        write_json(source_dir / file_name, rows)
    for type_name, rows in group_by_type(export_data, "target").items():
        file_name = safe_file_name(type_name) + ".json"
        write_json(target_dir / file_name, rows)
    files.extend(["mappings_by_source_type/", "mappings_by_target_type/"])

    report = {
        "status": "SUCCESS" if not errors else "COMPLETED_WITH_ERRORS",
        "dryRun": False,
        "mappingsListed": len(summaries),
        "mappingsExported": len(export_data),
        "attributeMappingsExported": len(property_rows),
        "sourcesAndTargets": len(source_target_rows),
        "warningCount": len(warnings),
        "errorCount": len(errors),
        "warnings": warnings,
        "errors": errors,
        "filters": {"sourceId": source_id or "", "targetId": target_id or ""},
    }
    write_json(output_dir / "execution_report.json", report)
    files.append("execution_report.json")
    write_json(output_dir / "manifest.json", manifest("export", config_path, files, dry_run=False))
    return output_dir


def safe_file_name(value: str) -> str:
    clean = "".join(char.lower() if char.isalnum() else "_" for char in value.strip())
    clean = "_".join(part for part in clean.split("_") if part)
    return clean or "unknown"
