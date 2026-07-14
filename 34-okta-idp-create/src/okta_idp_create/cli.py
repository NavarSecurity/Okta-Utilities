from __future__ import annotations

import argparse
import sys
from typing import Any

from .config import ConfigError, load_config, load_idp_input
from .okta_client import OktaApiError, OktaClient, find_existing_by_name
from .planner import build_plan
from .redact import redact_object
from .reports import create_run_dir, write_standard_reports


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create external IdPs in Okta from JSON configuration.")
    parser.add_argument("--config", required=True, help="Path to config.json")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Preview planned actions without creating IdPs")
    mode.add_argument("--apply", action="store_true", help="Create IdPs in Okta")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    dry_run = not args.apply

    try:
        config = load_config(args.config)
        idp_input = load_idp_input(config.input_file)
        plan = build_plan(idp_input)
        run_dir = create_run_dir(config.output_directory)

        redacted_payloads = [
            {
                "name": item["name"],
                "type": item["type"],
                "payload": redact_object(item["payload"]) if config.redact_sensitive_values else item["payload"],
            }
            for item in plan
        ]

        existing_idps: list[dict[str, Any]] = []
        client: OktaClient | None = None
        if config.check_existing or args.apply:
            try:
                client = OktaClient.from_env(config.timeout_seconds)
                existing_idps = client.list_identity_providers() if config.check_existing else []
            except OktaApiError:
                if args.apply:
                    raise
                # Dry-run can still produce a useful validation report without live access.
                existing_idps = []
                client = None

        planned: list[dict[str, Any]] = []
        created: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []
        rollback_actions: list[dict[str, Any]] = []

        for item in plan:
            existing = find_existing_by_name(existing_idps, item["name"]) if config.check_existing else None
            if existing:
                message = f"Identity Provider already exists with id {existing.get('id', '')}"
                record = {
                    "name": item["name"],
                    "type": item["type"],
                    "action": "create",
                    "result": "skipped" if config.on_existing == "skip" else "failed",
                    "id": existing.get("id", ""),
                    "message": message,
                }
                if config.on_existing == "skip":
                    skipped.append(record)
                    continue
                failed.append(record)
                continue

            planned_record = {
                "name": item["name"],
                "type": item["type"],
                "action": "create",
                "result": "planned" if dry_run else "pending",
                "message": "Identity Provider will be created" if dry_run else "Identity Provider queued for creation",
            }
            planned.append(planned_record)

            if dry_run:
                continue

            if client is None:
                client = OktaClient.from_env(config.timeout_seconds)
            try:
                created_idp = client.create_identity_provider(item["payload"])
                idp_id = created_idp.get("id", "")
                if config.activate_after_create and idp_id:
                    client.activate_identity_provider(idp_id)
                created.append(
                    {
                        "name": item["name"],
                        "type": item["type"],
                        "action": "create",
                        "result": "created",
                        "id": idp_id,
                        "message": "Identity Provider created" + (" and activation requested" if config.activate_after_create else ""),
                    }
                )
                if idp_id:
                    rollback_actions.append(
                        {
                            "action": "delete",
                            "idpId": idp_id,
                            "name": item["name"],
                            "reason": "Rollback created IdP from utility 34 apply run",
                        }
                    )
            except Exception as exc:  # noqa: BLE001 - record per-object failure and continue
                failed.append(
                    {
                        "name": item["name"],
                        "type": item["type"],
                        "action": "create",
                        "result": "failed",
                        "message": str(exc),
                    }
                )

        write_standard_reports(
            run_dir=run_dir,
            planned=planned,
            redacted_payloads=redacted_payloads,
            created=created,
            skipped=skipped,
            failed=failed,
            rollback_actions=rollback_actions,
            dry_run=dry_run,
            config_path=args.config,
            input_path=str(config.input_file),
        )

        print(f"Output written to: {run_dir}")
        print(f"Planned: {len(planned)} Created: {len(created)} Skipped: {len(skipped)} Failed: {len(failed)}")
        return 1 if failed else 0
    except (ConfigError, OktaApiError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
