from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .backup import BackupError
from .client import OktaClient
from .config import ConfigError, load_config
from .loader import execute_plan
from .planner import build_plan
from .reporting import make_run_dir, write_outputs


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="okta-app-cloner",
        description="Clone selected Okta application configuration from an okta-config-backup export into a target Okta org.",
    )
    parser.add_argument("--config", default="input/cloner.config.json", help="Path to app cloner config JSON file.")
    parser.add_argument("--source-backup-dir", help="Override source backup directory from config.")
    parser.add_argument("--output-dir", help="Override output directory from config.")
    parser.add_argument("--labels", help="Comma-separated app labels to clone. Overrides selection.applications.labels from config.")
    parser.add_argument("--ids", help="Comma-separated source app IDs to clone. Overrides selection.applications.ids from config.")
    parser.add_argument("--dry-run", action="store_true", help="Plan, validate, and check target for duplicate labels, but do not create apps. This is the default.")
    parser.add_argument("--apply", action="store_true", help="Actually create selected apps in the target Okta org.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def _comma_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = load_config(args.config)
        if args.source_backup_dir:
            config.source_backup_dir = Path(args.source_backup_dir)
            if not config.source_backup_dir.exists():
                raise ConfigError(f"Source backup directory not found: {config.source_backup_dir}")
        if args.output_dir:
            config.output_dir = Path(args.output_dir)
        if args.labels:
            config.selection.setdefault("applications", {})["labels"] = _comma_list(args.labels)
            config.selection.setdefault("applications", {})["ids"] = []
        if args.ids:
            config.selection.setdefault("applications", {})["ids"] = _comma_list(args.ids)
            config.selection.setdefault("applications", {})["labels"] = []

        apply = bool(args.apply)
        if args.apply and args.dry_run:
            raise ConfigError("Use either --dry-run or --apply, not both.")

        plan = build_plan(config)
        client = OktaClient(
            config.target_org_url,
            config.target_api_token,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
            retry_base_seconds=config.retry_base_seconds,
            page_limit=config.page_limit,
        )
        result = execute_plan(client, config, plan, apply=apply)
        run_dir = make_run_dir(config.output_dir)
        files = write_outputs(run_dir, config, plan, result, apply=apply)

        print(f"Okta app clone {'applied' if apply else 'dry-run complete'}: {run_dir}")
        print(f"Plan: {files['plan']}")
        print(f"Result: {files['result']}")
        print(f"Rollback: {files['rollback']}")
        print(f"Mapping: {files['mapping']}")
        print(f"Report: {files['report']}")
        if result.has_errors():
            print(f"Completed with {len(result.errors)} recorded error(s). Review clone_result.json.", file=sys.stderr)
            return 1
        return 0

    except (ConfigError, BackupError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Runtime error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
