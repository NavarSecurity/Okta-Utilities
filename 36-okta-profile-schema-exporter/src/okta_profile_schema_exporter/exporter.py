from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import ExportConfig
from .normalize import summarize_app, summarize_schema, summarize_schema_header
from .okta_client import OktaApiError, OktaClient
from .redact import redact_object
from .reports import create_run_dir, safe_filename, write_csv, write_execution_report, write_json, write_manifest


def _load_app_identifiers_from_file(path: str) -> list[str]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    values: list[str] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        clean = line.strip()
        if not clean or clean.startswith("#"):
            continue
        values.append(clean)
    return values



def _is_excluded_okta_system_app(config: ExportConfig, app: dict[str, Any]) -> bool:
    if not config.skip_okta_system_apps:
        return False
    excluded_names = {name.lower() for name in config.excluded_app_names}
    return str(app.get("name", "")).lower() in excluded_names


def _split_exportable_apps(config: ExportConfig, apps: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    exportable_apps: list[dict[str, Any]] = []
    skipped_apps: list[dict[str, Any]] = []
    for app in apps:
        if _is_excluded_okta_system_app(config, app):
            skipped_apps.append(app)
        else:
            exportable_apps.append(app)
    return exportable_apps, skipped_apps


def _select_apps(config: ExportConfig, apps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mode = config.app_selection.mode
    if mode == "none":
        return []
    if mode == "all":
        return apps
    if mode == "ids":
        wanted = set(config.app_selection.app_ids)
        return [app for app in apps if app.get("id") in wanted]
    if mode == "names":
        wanted = {name.lower() for name in config.app_selection.app_names}
        return [
            app for app in apps
            if str(app.get("label", "")).lower() in wanted or str(app.get("name", "")).lower() in wanted
        ]
    if mode == "file":
        values = _load_app_identifiers_from_file(config.app_selection.app_file)
        wanted = {value.lower() for value in values}
        return [
            app for app in apps
            if str(app.get("id", "")).lower() in wanted
            or str(app.get("label", "")).lower() in wanted
            or str(app.get("name", "")).lower() in wanted
        ]
    return []


def export_profile_schemas(config: ExportConfig, dry_run: bool = False) -> Path:
    run_dir = create_run_dir(config.output_directory)
    warnings: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    output_files: list[str] = []

    if dry_run:
        report = {
            "status": "DRY_RUN",
            "message": "Configuration validated. No Okta API calls were made.",
            "planned": {
                "includeUserSchemas": config.include_user_schemas,
                "userSchemaIds": config.user_schema_ids,
                "includeGroupSchema": config.include_group_schema,
                "includeAppSchemas": config.include_app_schemas,
                "appSelectionMode": config.app_selection.mode,
                "includeInactiveApps": config.include_inactive_apps,
                "skipOktaSystemApps": config.skip_okta_system_apps,
                "excludedAppNames": config.excluded_app_names,
            },
            "warnings": warnings,
            "errors": errors,
        }
        write_execution_report(run_dir, report)
        output_files.append("execution_report.json")
        write_manifest(run_dir, "dry-run", output_files, config.raw)
        return run_dir

    assert config.okta_org_url is not None
    assert config.okta_api_token is not None
    client = OktaClient(config.okta_org_url, config.okta_api_token, config.timeout_seconds, config.max_retries)

    user_schemas: list[dict[str, Any]] = []
    group_schema: dict[str, Any] | None = None
    apps: list[dict[str, Any]] = []
    exportable_apps: list[dict[str, Any]] = []
    skipped_apps: list[dict[str, Any]] = []
    selected_apps: list[dict[str, Any]] = []
    app_schemas: list[dict[str, Any]] = []
    app_failures: list[dict[str, Any]] = []
    schema_rows: list[dict[str, Any]] = []

    if config.include_user_schemas:
        for schema_id in config.user_schema_ids:
            try:
                schema = client.get_user_schema(schema_id)
                if config.redact_sensitive_values:
                    schema = redact_object(schema)
                user_schemas.append({"schemaId": schema_id, "schema": schema})
                schema_rows.extend(summarize_schema("user", schema, {"schemaLookupId": schema_id}))
                if config.write_individual_schema_files:
                    file_name = f"schemas_by_user_type/{safe_filename(schema_id)}.json"
                    write_json(run_dir / file_name, schema)
                    output_files.append(file_name)
            except OktaApiError as exc:
                errors.append({"category": "userSchema", "schemaId": schema_id, "message": str(exc), "statusCode": exc.status_code})

    if config.include_group_schema:
        try:
            group_schema = client.get_group_schema()
            if config.redact_sensitive_values:
                group_schema = redact_object(group_schema)
            schema_rows.extend(summarize_schema("group", group_schema))
        except OktaApiError as exc:
            errors.append({"category": "groupSchema", "message": str(exc), "statusCode": exc.status_code})

    if config.include_app_schemas and config.app_selection.mode != "none":
        try:
            apps = client.list_apps(config.include_inactive_apps)
            exportable_apps, skipped_apps = _split_exportable_apps(config, apps)
            selected_apps = _select_apps(config, exportable_apps)
            if config.app_selection.mode in {"ids", "names", "file"}:
                requested_count = {
                    "ids": len(config.app_selection.app_ids),
                    "names": len(config.app_selection.app_names),
                    "file": len(_load_app_identifiers_from_file(config.app_selection.app_file)),
                }[config.app_selection.mode]
                if requested_count != len(selected_apps):
                    warnings.append(
                        {
                            "category": "appSelection",
                            "message": f"Requested {requested_count} app identifiers but selected {len(selected_apps)} apps from the org."
                        }
                    )
        except OktaApiError as exc:
            errors.append({"category": "appList", "message": str(exc), "statusCode": exc.status_code})
            selected_apps = []

        for app in selected_apps:
            app_summary = summarize_app(app)
            app_id = str(app_summary.get("id"))
            try:
                schema = client.get_app_user_schema(app_id)
                if config.redact_sensitive_values:
                    schema = redact_object(schema)
                app_record = {"app": app_summary, "schema": schema}
                app_schemas.append(app_record)
                schema_rows.extend(
                    summarize_schema(
                        "app",
                        schema,
                        {
                            "appId": app_summary.get("id", ""),
                            "appLabel": app_summary.get("label", ""),
                            "appName": app_summary.get("name", ""),
                            "appStatus": app_summary.get("status", ""),
                        },
                    )
                )
                if config.write_individual_schema_files:
                    file_name = f"schemas_by_app/{safe_filename(app_summary.get('label') or app_id)}_{safe_filename(app_id)}.json"
                    write_json(run_dir / file_name, app_record)
                    output_files.append(file_name)
            except OktaApiError as exc:
                failure = {
                    "appId": app_summary.get("id", ""),
                    "appLabel": app_summary.get("label", ""),
                    "appName": app_summary.get("name", ""),
                    "statusCode": exc.status_code,
                    "message": str(exc),
                }
                app_failures.append(failure)
                if not config.continue_on_app_schema_error:
                    errors.append({"category": "appSchema", **failure})
                    break
                warnings.append({"category": "appSchema", **failure})

    if user_schemas:
        write_json(run_dir / "user_schemas_full.json", user_schemas)
        output_files.append("user_schemas_full.json")
    if group_schema is not None:
        write_json(run_dir / "group_schema_full.json", group_schema)
        output_files.append("group_schema_full.json")
    if apps:
        write_json(run_dir / "apps_inventory.json", [summarize_app(app) for app in exportable_apps])
        output_files.append("apps_inventory.json")
    if skipped_apps:
        skipped_rows = [
            {
                **summarize_app(app),
                "reason": "Okta system/internal app excluded from app schema export",
            }
            for app in skipped_apps
        ]
        write_json(run_dir / "skipped_apps.json", skipped_rows)
        write_csv(run_dir / "skipped_apps.csv", skipped_rows, ["id", "label", "name", "status", "signOnMode", "reason"])
        output_files.extend(["skipped_apps.json", "skipped_apps.csv"])
    if selected_apps:
        write_json(run_dir / "selected_apps.json", [summarize_app(app) for app in selected_apps])
        output_files.append("selected_apps.json")
    if app_schemas:
        write_json(run_dir / "app_schemas_full.json", app_schemas)
        output_files.append("app_schemas_full.json")
    if app_failures:
        write_csv(run_dir / "app_schema_failures.csv", app_failures, ["appId", "appLabel", "appName", "statusCode", "message"])
        output_files.append("app_schema_failures.csv")

    if schema_rows:
        header = summarize_schema_header()
        write_csv(run_dir / "profile_schema_attributes.csv", schema_rows, header)
        output_files.append("profile_schema_attributes.csv")

        summary_rows = [
            {
                "schemaCategory": row["schemaCategory"],
                "schemaId": row["schemaId"],
                "schemaName": row["schemaName"],
                "appId": row["appId"],
                "appLabel": row["appLabel"],
                "attributeCount": "",
            }
            for row in schema_rows
        ]
        # Compact summary by schema/app tuple.
        grouped: dict[tuple[str, str, str, str], int] = {}
        for row in schema_rows:
            key = (row["schemaCategory"], row["schemaId"], row["schemaName"], row["appLabel"] or row["appId"])
            grouped[key] = grouped.get(key, 0) + 1
        compact = [
            {
                "schemaCategory": key[0],
                "schemaId": key[1],
                "schemaName": key[2],
                "appOrSchema": key[3],
                "attributeCount": count,
            }
            for key, count in sorted(grouped.items())
        ]
        write_csv(run_dir / "schema_summary.csv", compact, ["schemaCategory", "schemaId", "schemaName", "appOrSchema", "attributeCount"])
        output_files.append("schema_summary.csv")

    status = "SUCCESS" if not errors else "COMPLETED_WITH_ERRORS"
    report = {
        "status": status,
        "counts": {
            "userSchemasRequested": len(config.user_schema_ids) if config.include_user_schemas else 0,
            "userSchemasExported": len(user_schemas),
            "groupSchemaExported": 1 if group_schema is not None else 0,
            "appsDiscovered": len(apps),
            "appsSkipped": len(skipped_apps),
            "appsEligible": len(exportable_apps),
            "appsSelected": len(selected_apps),
            "appSchemasExported": len(app_schemas),
            "appSchemaFailures": len(app_failures),
            "attributeRows": len(schema_rows),
            "warnings": len(warnings),
            "errors": len(errors),
        },
        "warnings": warnings,
        "errors": errors,
    }
    write_execution_report(run_dir, report)
    output_files.append("execution_report.json")
    write_manifest(run_dir, "export", output_files, config.raw)
    return run_dir
