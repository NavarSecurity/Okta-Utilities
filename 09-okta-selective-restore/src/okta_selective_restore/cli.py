from __future__ import annotations

import argparse
import sys

from . import __version__
from .client import OktaClient
from .config import ConfigError, load_config
from .loader import execute_plan
from .planner import build_plan
from .reporting import make_run_dir, write_outputs


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="okta-selective-restore",
        description="Recreate selected Okta objects from an okta-config-backup export into a target Okta org.",
    )
    parser.add_argument("--config", default="input/restore.config.json", help="Path to restore config JSON file.")
    parser.add_argument("--source-backup-dir", help="Override source backup directory from config.")
    parser.add_argument("--output-dir", help="Override output directory from config.")
    parser.add_argument("--include", help="Comma-separated resource list to restore, for example groups,applications.")
    parser.add_argument("--dry-run", action="store_true", help="Plan and check target for duplicates, but do not create anything. This is the default.")
    parser.add_argument("--apply", action="store_true", help="Actually create selected objects in the target Okta org.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = load_config(args.config)
        if args.source_backup_dir:
            from pathlib import Path

            config.source_backup_dir = Path(args.source_backup_dir)
            if not config.source_backup_dir.exists():
                raise ConfigError(f"Source backup directory not found: {config.source_backup_dir}")
        if args.output_dir:
            from pathlib import Path

            config.output_dir = Path(args.output_dir)
        if args.include:
            config.include = [part.strip() for part in args.include.split(",") if part.strip()]

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

        print(f"Selective restore {'applied' if apply else 'dry-run complete'}: {run_dir}")
        print(f"Plan: {files['plan']}")
        print(f"Result: {files['result']}")
        print(f"Rollback: {files['rollback']}")
        print(f"Report: {files['report']}")
        if result.has_errors():
            print(f"Completed with {len(result.errors)} recorded error(s). Review restore_result.json.", file=sys.stderr)
            return 1
        return 0

    except ConfigError as exc:
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
