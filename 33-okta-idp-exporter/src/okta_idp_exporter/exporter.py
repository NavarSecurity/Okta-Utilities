from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import RuntimeConfig
from .normalize import count_by_field, idp_status, idp_type, should_include_idp, summarize_idp, summarize_key
from .okta_client import OktaClient, OktaApiError
from .redact import prepare_export_object
from .reports import build_manifest, ensure_dir, relative_files, utc_timestamp, write_csv, write_json


IDP_SUMMARY_FIELDS = [
    "id",
    "name",
    "type",
    "status",
    "protocolType",
    "issuerMode",
    "issuer",
    "clientId",
    "authorizationUrl",
    "tokenUrl",
    "jwksUrl",
    "ssoUrl",
    "signatureAlgorithm",
    "accountLinkFilter",
    "accountLinkAction",
    "provisioningAction",
    "created",
    "lastUpdated",
]

KEY_SUMMARY_FIELDS = ["kid", "kty", "use", "alg", "status", "created", "lastUpdated", "expiresAt"]


def export_idps(runtime: RuntimeConfig, config_path: str, dry_run: bool = False) -> Path:
    app = runtime.app
    timestamp = utc_timestamp()
    run_dir = ensure_dir(Path(app.output_dir) / f"idp-export-{timestamp}")

    execution_report: dict[str, Any] = {
        "utility": "okta-idp-exporter",
        "operation": "export",
        "dryRun": dry_run,
        "startedAt": timestamp,
        "counts": {},
        "warnings": [],
        "errors": [],
    }

    if dry_run:
        execution_report["counts"] = {
            "identityProvidersExported": 0,
            "identityProviderKeysExported": 0,
        }
        execution_report["plannedActions"] = [
            "GET /api/v1/idps?limit=200",
            "GET /api/v1/idps/credentials/keys?limit=200" if app.include_keys else "Skip IdP key export",
            "Write redacted JSON, summary CSV, execution report, and manifest output",
        ]
        write_json(run_dir / "execution_report.json", execution_report)
        write_json(run_dir / "manifest.json", build_manifest("export", run_dir, config_path, relative_files(run_dir)))
        return run_dir

    if not runtime.org_url or not runtime.api_token:
        raise ValueError("OKTA_ORG_URL and OKTA_API_TOKEN are required for export mode.")

    client = OktaClient(runtime.org_url, runtime.api_token)

    try:
        raw_idps = client.list_identity_providers()
    except OktaApiError as exc:
        execution_report["errors"].append({"request": "GET /api/v1/idps", "message": str(exc), "payload": exc.payload})
        write_json(run_dir / "execution_report.json", execution_report)
        raise

    filtered_raw_idps = [
        idp
        for idp in raw_idps
        if should_include_idp(
            idp,
            include_inactive=app.include_inactive,
            types=app.filters.types,
            statuses=app.filters.statuses,
        )
    ]

    exported_idps = [
        prepare_export_object(
            idp,
            include_links=app.include_links,
            redact_sensitive=app.redact_sensitive_values,
            redaction_config=app.redaction,
        )
        for idp in filtered_raw_idps
    ]

    idp_summaries = [summarize_idp(idp) for idp in exported_idps]

    write_json(run_dir / "idps_full.json", {"identityProviders": exported_idps})
    write_csv(run_dir / "idps_summary.csv", idp_summaries, IDP_SUMMARY_FIELDS)

    if app.split_by_type:
        by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for idp in exported_idps:
            by_type[idp_type(idp)].append(idp)
        for current_type, items in by_type.items():
            write_json(run_dir / "idps_by_type" / f"{current_type.lower()}_idps.json", {"identityProviders": items})

    key_summaries: list[dict[str, Any]] = []
    exported_keys: list[dict[str, Any]] = []
    if app.include_keys:
        try:
            raw_keys = client.list_identity_provider_keys()
            exported_keys = [
                prepare_export_object(
                    key,
                    include_links=app.include_links,
                    redact_sensitive=app.redact_sensitive_values,
                    redaction_config=app.redaction,
                )
                for key in raw_keys
            ]
            key_summaries = [summarize_key(key) for key in exported_keys]
            write_json(run_dir / "idp_keys.json", {"keys": exported_keys})
            write_csv(run_dir / "idp_keys_summary.csv", key_summaries, KEY_SUMMARY_FIELDS)
        except OktaApiError as exc:
            execution_report["warnings"].append(
                {
                    "request": "GET /api/v1/idps/credentials/keys",
                    "message": str(exc),
                    "payload": exc.payload,
                    "note": "IdP configuration export completed, but IdP key export failed.",
                }
            )

    execution_report["counts"] = {
        "identityProvidersReturnedByApi": len(raw_idps),
        "identityProvidersExported": len(exported_idps),
        "identityProviderKeysExported": len(exported_keys),
        "byType": count_by_field(exported_idps, "type"),
        "byStatus": count_by_field(exported_idps, "status"),
    }
    execution_report["completedAt"] = utc_timestamp()

    write_json(run_dir / "execution_report.json", execution_report)
    write_json(run_dir / "manifest.json", build_manifest("export", run_dir, config_path, relative_files(run_dir)))
    return run_dir
