from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import ExportConfig
from .okta_client import OktaClient, OktaClientError
from .normalize import (
    app_display_name,
    connector_details,
    flatten_mapping_properties,
    flatten_schema_attributes,
    mapping_involves_app,
    provisioning_feature_rows,
    is_feature_not_applicable,
    select_apps,
    should_skip_app,
    summarize_app,
)
from .redact import redact_object
from .reports import make_run_dir, write_csv, write_json, write_manifest


def dry_run(cfg: ExportConfig) -> dict[str, Any]:
    """Validate configuration and write dry-run evidence without calling Okta."""
    run_dir = make_run_dir(cfg.output_directory, prefix="app-provisioning-dry-run")
    files: list[str] = []

    config_summary = {
        "outputDirectory": cfg.output_directory,
        "appSelection": {
            "mode": cfg.app_selection.mode,
            "appIdsCount": len(cfg.app_selection.app_ids),
            "appNamesCount": len(cfg.app_selection.app_names),
            "appFile": cfg.app_selection.app_file,
        },
        "includeInactiveApps": cfg.include_inactive_apps,
        "includeAppSchemas": cfg.include_app_schemas,
        "includeProfileMappings": cfg.include_profile_mappings,
        "includeAppFeatures": cfg.include_app_features,
        "includeConnectorDetails": cfg.include_connector_details,
        "skipOktaSystemApps": cfg.skip_okta_system_apps,
        "continueOnAppSchemaError": cfg.continue_on_app_schema_error,
        "redactSensitiveValues": cfg.redact_sensitive_values,
        "excludedAppNames": cfg.excluded_app_names,
        "timeoutSeconds": cfg.timeout_seconds,
    }

    planned_outputs = [
        "apps_full.json",
        "apps_summary.csv",
        "connector_details.csv",
        "provisioning_features.csv",
        "app_schemas_full.json",
        "app_schema_attributes.csv",
        "profile_mappings_full.json",
        "profile_mapping_properties.csv",
        "selected_apps.json",
        "skipped_apps.json",
        "skipped_apps.csv",
        "app_schema_failures.csv",
        "feature_request_failures.csv",
        "feature_not_applicable.csv",
        "execution_report.json",
        "manifest.json",
        "apps_by_name/",
    ]

    dry_run_report = {
        "status": "DRY_RUN_SUCCESS",
        "message": "Configuration validation completed. No Okta API calls were made.",
        "willCallOkta": False,
        "willModifyOkta": False,
        "plannedOperation": "app-provisioning-export",
        "plannedOutputs": planned_outputs,
        "configSummary": config_summary,
    }

    write_json(run_dir / "dry_run_report.json", dry_run_report)
    files.append("dry_run_report.json")
    write_json(run_dir / "config_summary.json", config_summary)
    files.append("config_summary.json")

    execution_report = {
        "status": "DRY_RUN_SUCCESS",
        "appsDiscovered": 0,
        "appsEligible": 0,
        "appsSelected": 0,
        "appsSkipped": 0,
        "appSchemasExported": 0,
        "appSchemaFailures": 0,
        "profileMappingsExported": 0,
        "profileMappingPropertyRows": 0,
        "featureRequestFailures": 0,
        "featureNotApplicable": 0,
        "warnings": [],
        "message": "Dry run only. No Okta API calls were made and no app data was exported.",
    }
    write_json(run_dir / "execution_report.json", execution_report)
    files.append("execution_report.json")
    write_manifest(run_dir, "app-provisioning-dry-run", files)
    files.append("manifest.json")

    return {**execution_report, "outputDirectory": str(run_dir)}


def export(cfg: ExportConfig) -> dict[str, Any]:
    client = OktaClient(timeout_seconds=cfg.timeout_seconds)
    run_dir = make_run_dir(cfg.output_directory)
    files: list[str] = []
    warnings: list[str] = []

    apps = client.list_apps()
    eligible_apps: list[dict[str, Any]] = []
    skipped_apps: list[dict[str, Any]] = []
    for app in apps:
        skip, reason = should_skip_app(app, cfg.include_inactive_apps, cfg.skip_okta_system_apps, cfg.excluded_app_names)
        if skip:
            skipped_apps.append({"id": app.get("id"), "name": app.get("name"), "label": app.get("label"), "reason": reason})
        else:
            eligible_apps.append(app)

    selected_apps, not_selected = select_apps(
        eligible_apps,
        cfg.app_selection.mode,
        cfg.app_selection.app_ids,
        cfg.app_selection.app_names,
        cfg.app_selection.app_file,
    )
    skipped_apps.extend(not_selected)

    app_features: dict[str, Any] = {}
    feature_failures: list[dict[str, Any]] = []
    feature_not_applicable: list[dict[str, Any]] = []
    if cfg.include_app_features:
        for app in selected_apps:
            status, payload, text = client.get_app_features_with_status(str(app.get("id")))
            if status < 400:
                app_features[str(app.get("id"))] = payload
            elif is_feature_not_applicable(status, payload, text):
                feature_not_applicable.append({
                    "appId": app.get("id"),
                    "appName": app.get("name"),
                    "appLabel": app.get("label"),
                    "statusCode": status,
                    "reason": "provisioning_not_supported",
                    "message": str(text)[:500],
                })
            else:
                feature_failures.append({
                    "appId": app.get("id"),
                    "appName": app.get("name"),
                    "appLabel": app.get("label"),
                    "statusCode": status,
                    "message": str(text)[:500],
                })
                warnings.append(f"Feature request failed for {app_display_name(app)} with status {status}")

    apps_full = redact_object(selected_apps) if cfg.redact_sensitive_values else selected_apps
    write_json(run_dir / "apps_full.json", apps_full)
    files.append("apps_full.json")
    write_csv(run_dir / "apps_summary.csv", [summarize_app(app) for app in selected_apps])
    files.append("apps_summary.csv")
    write_json(run_dir / "selected_apps.json", [{"id": a.get("id"), "name": a.get("name"), "label": a.get("label"), "status": a.get("status")} for a in selected_apps])
    files.append("selected_apps.json")
    write_json(run_dir / "skipped_apps.json", skipped_apps)
    files.append("skipped_apps.json")
    write_csv(run_dir / "skipped_apps.csv", skipped_apps)
    files.append("skipped_apps.csv")

    if cfg.include_connector_details:
        write_csv(run_dir / "connector_details.csv", [connector_details(app, app_features.get(str(app.get("id")))) for app in selected_apps])
        files.append("connector_details.csv")

    feature_rows = []
    for app in selected_apps:
        feature_rows.extend(provisioning_feature_rows(app, app_features.get(str(app.get("id")))))
    write_csv(run_dir / "provisioning_features.csv", feature_rows)
    files.append("provisioning_features.csv")
    write_csv(run_dir / "feature_request_failures.csv", feature_failures)
    files.append("feature_request_failures.csv")
    write_csv(run_dir / "feature_not_applicable.csv", feature_not_applicable)
    files.append("feature_not_applicable.csv")

    schema_exports: list[dict[str, Any]] = []
    schema_rows: list[dict[str, Any]] = []
    schema_failures: list[dict[str, Any]] = []
    if cfg.include_app_schemas:
        for app in selected_apps:
            status, payload, text = client.get_app_schema_with_status(str(app.get("id")))
            if status < 400 and isinstance(payload, dict):
                schema_record = {"app": {"id": app.get("id"), "name": app.get("name"), "label": app.get("label")}, "schema": redact_object(payload) if cfg.redact_sensitive_values else payload}
                schema_exports.append(schema_record)
                schema_rows.extend(flatten_schema_attributes(app, payload))
            else:
                failure = {"appId": app.get("id"), "appName": app.get("name"), "appLabel": app.get("label"), "statusCode": status, "message": str(text)[:500]}
                schema_failures.append(failure)
                warnings.append(f"App schema export failed for {app_display_name(app)} with status {status}")
                if not cfg.continue_on_app_schema_error:
                    raise OktaClientError(f"App schema export failed for {app_display_name(app)} with status {status}")
    write_json(run_dir / "app_schemas_full.json", schema_exports)
    files.append("app_schemas_full.json")
    write_csv(run_dir / "app_schema_attributes.csv", schema_rows)
    files.append("app_schema_attributes.csv")
    write_csv(run_dir / "app_schema_failures.csv", schema_failures)
    files.append("app_schema_failures.csv")

    related_mappings: list[dict[str, Any]] = []
    mapping_rows: list[dict[str, Any]] = []
    if cfg.include_profile_mappings:
        all_mappings = client.list_profile_mappings()
        selected_ids = {str(app.get("id")) for app in selected_apps}
        mapping_summaries = [m for m in all_mappings if mapping_involves_app(m, selected_ids)]
        for summary in mapping_summaries:
            mapping = summary
            # Okta's list endpoint may return mapping metadata without the full property map.
            # Fetch the individual mapping when an id is present so attribute-level exports are useful.
            if not mapping.get("properties") and mapping.get("id"):
                try:
                    mapping = client.get_profile_mapping(str(mapping.get("id")))
                except Exception as exc:
                    warnings.append(f"Profile mapping detail export failed for {mapping.get('id')}: {exc}")
            related_mappings.append(mapping)
            mapping_rows.extend(flatten_mapping_properties(mapping))
    write_json(run_dir / "profile_mappings_full.json", redact_object(related_mappings) if cfg.redact_sensitive_values else related_mappings)
    files.append("profile_mappings_full.json")
    write_csv(run_dir / "profile_mapping_properties.csv", mapping_rows)
    files.append("profile_mapping_properties.csv")

    apps_by_name = run_dir / "apps_by_name"
    apps_by_name.mkdir(exist_ok=True)
    for app in selected_apps:
        safe_name = _safe_file_name(str(app.get("label") or app.get("name") or app.get("id")))
        write_json(apps_by_name / f"{safe_name}.json", redact_object(app) if cfg.redact_sensitive_values else app)
    files.append("apps_by_name/")

    report = {
        "status": "SUCCESS",
        "appsDiscovered": len(apps),
        "appsEligible": len(eligible_apps),
        "appsSelected": len(selected_apps),
        "appsSkipped": len(skipped_apps),
        "appSchemasExported": len(schema_exports),
        "appSchemaFailures": len(schema_failures),
        "profileMappingsExported": len(related_mappings),
        "profileMappingPropertyRows": len(mapping_rows),
        "featureRequestFailures": len(feature_failures),
        "featureNotApplicable": len(feature_not_applicable),
        "warnings": warnings,
    }
    write_json(run_dir / "execution_report.json", report)
    files.append("execution_report.json")
    write_manifest(run_dir, "app-provisioning-export", files)
    return {**report, "outputDirectory": str(run_dir)}


def _safe_file_name(value: str) -> str:
    keep = []
    for ch in value:
        if ch.isalnum() or ch in {"-", "_"}:
            keep.append(ch)
        elif ch.isspace():
            keep.append("_")
    return "".join(keep).strip("_")[:80] or "app"
