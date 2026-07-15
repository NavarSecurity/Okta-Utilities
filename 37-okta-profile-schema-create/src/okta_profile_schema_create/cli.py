from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from .config import ConfigError, load_input_file, load_settings
from .okta_client import OktaClient
from .operations import apply_plan
from .planner import create_plan
from .redact import redact
from .reports import create_run_directory, utc_timestamp, write_csv, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create Okta custom profile schema attributes from config.")
    parser.add_argument("--config", default="config.json", help="Path to config JSON file.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Preview planned schema changes without applying them.")
    mode.add_argument("--apply", action="store_true", help="Apply planned schema changes to Okta.")
    return parser


def _build_client(settings, require_credentials: bool) -> OktaClient | None:
    if not settings.okta_org_url or not settings.okta_api_token:
        if require_credentials:
            raise ConfigError("OKTA_ORG_URL and OKTA_API_TOKEN are required for this operation.")
        return None
    return OktaClient(settings.okta_org_url, settings.okta_api_token, timeout_seconds=settings.timeout_seconds)


def _summary_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "index": item.get("index"),
            "status": item.get("status"),
            "action": item.get("action"),
            "targetType": item.get("targetType"),
            "schemaId": item.get("schemaId"),
            "appId": item.get("appId"),
            "appName": item.get("appName"),
            "attributeName": item.get("attributeName"),
            "reason": item.get("reason"),
            "error": item.get("error"),
        }
        for item in items
    ]


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    dry_run = args.dry_run or not args.apply

    try:
        settings = load_settings(args.config)
        input_data = load_input_file(settings.input_file)
        client = _build_client(settings, require_credentials=settings.check_existing or args.apply)

        run_dir = create_run_directory(settings.output_directory, "profile-schema-create")
        plan = create_plan(settings, input_data, client)
        planned_items = [item.as_dict() for item in plan.planned]
        error_items = [item.as_dict() for item in plan.errors]
        all_items = planned_items + error_items
        redacted_items = redact(all_items) if settings.redact_sensitive_values else all_items

        write_json(run_dir / "planned_changes.json", redacted_items)
        write_csv(
            run_dir / "planned_changes.csv",
            _summary_rows(redacted_items),
            ["index", "status", "action", "targetType", "schemaId", "appId", "appName", "attributeName", "reason", "error"],
        )
        write_json(run_dir / "redacted_payloads.json", redact([item.get("payload") for item in all_items]))

        applied: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        rollback_actions: list[dict[str, Any]] = []
        if args.apply:
            if client is None:
                raise ConfigError("Okta client could not be initialized.")
            applicable = [item for item in plan.planned if item.action in {"create", "update"} and item.status == "planned"]
            applied, failures, rollback_actions = apply_plan(applicable, client)
            applied_out = redact(applied) if settings.redact_sensitive_values else applied
            failures_out = redact(failures) if settings.redact_sensitive_values else failures
            rollback_out = redact(rollback_actions) if settings.redact_sensitive_values else rollback_actions
            write_json(run_dir / "applied_changes.json", applied_out)
            write_json(run_dir / "failed_changes.json", failures_out)
            write_json(run_dir / "rollback_actions.json", rollback_out)
            write_csv(
                run_dir / "applied_changes.csv",
                _summary_rows(applied_out + failures_out),
                ["index", "status", "action", "targetType", "schemaId", "appId", "appName", "attributeName", "reason", "error"],
            )

        report = {
            "utility": "okta-profile-schema-create",
            "timestamp": utc_timestamp(),
            "mode": "dry-run" if dry_run else "apply",
            "status": "SUCCESS" if not failures and not error_items else ("PARTIAL_SUCCESS" if settings.continue_on_error else "FAILED"),
            "inputFile": str(settings.input_file),
            "outputDirectory": str(run_dir),
            "totalRequested": len(input_data.get("attributes", [])),
            "planned": sum(1 for item in plan.planned if item.status == "planned"),
            "skipped": sum(1 for item in plan.planned if item.status == "skipped"),
            "planErrors": len(plan.errors),
            "applied": len([item for item in applied if item.get("applyStatus") == "applied"]),
            "applyFailures": len(failures),
            "onExisting": settings.on_existing,
            "checkExisting": settings.check_existing,
        }
        write_json(run_dir / "execution_report.json", report)
        write_json(run_dir / "manifest.json", {
            "generatedAt": utc_timestamp(),
            "configFile": str(Path(args.config)),
            "inputFile": str(settings.input_file),
            "outputs": sorted(path.name for path in run_dir.iterdir()),
        })

        print(f"Output written to: {run_dir}")
        print(f"Status: {report['status']} | Planned: {report['planned']} | Skipped: {report['skipped']} | Errors: {report['planErrors']} | Applied: {report['applied']} | Apply failures: {report['applyFailures']}")
        return 1 if report["status"] == "FAILED" else 0
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"Unhandled error: {exc}", file=sys.stderr)
        return 1


def main() -> None:
    raise SystemExit(run())
