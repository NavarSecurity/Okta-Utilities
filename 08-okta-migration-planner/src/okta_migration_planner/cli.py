from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import build_config
from .io_utils import utc_timestamp
from .planner import MigrationPlanner, PlannerError
from .report import write_outputs


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="okta-migration-planner",
        description="Compare source and target Okta backup folders and generate a migration planning report.",
    )
    parser.add_argument("--config", help="Path to planner config JSON.")
    parser.add_argument("--source-backup-dir", help="Source Okta backup directory.")
    parser.add_argument("--target-backup-dir", help="Target Okta backup directory.")
    parser.add_argument("--output-dir", help="Output directory for generated planning artifacts.")
    parser.add_argument("--include", help="Comma-separated resource list to analyze.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as blocking in readiness status.")
    parser.add_argument("--print-json", action="store_true", help="Print the generated migration plan JSON to stdout.")
    parser.add_argument("--version", action="version", version=f"okta-migration-planner {__version__}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = build_config(
            config_path=Path(args.config) if args.config else None,
            source_backup_dir=args.source_backup_dir,
            target_backup_dir=args.target_backup_dir,
            output_dir=args.output_dir,
            include=args.include,
            strict=args.strict if args.strict else None,
        )
        run_dir = config.output_dir / f"okta-migration-plan-{utc_timestamp()}"
        planner = MigrationPlanner(config)
        plan = planner.build_plan()
        paths = write_outputs(run_dir, plan, write_csv_files=config.write_csv, write_markdown=config.write_markdown)

        if args.print_json:
            from dataclasses import asdict

            print(json.dumps(asdict(plan), indent=2, sort_keys=True))
        else:
            print(f"Migration plan complete: {run_dir}")
            print(f"Plan: {paths.get('migration_plan')}")
            if "cutover_readiness_report" in paths:
                print(f"Readiness: {paths.get('cutover_readiness_report')}")
            if "object_mapping" in paths:
                print(f"Object mapping: {paths.get('object_mapping')}")
            print(f"Overall status: {plan.overall_status}")

        if plan.overall_status in {"NOT_READY", "READY_WITH_WARNINGS_BLOCKED_BY_STRICT_MODE"}:
            return 1
        return 0
    except (ValueError, PlannerError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"UNEXPECTED ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
