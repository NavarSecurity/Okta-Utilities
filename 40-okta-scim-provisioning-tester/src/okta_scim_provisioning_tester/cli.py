from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config, load_test_plan
from .operations import execute_plan, write_dry_run
from .planner import build_plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Test downstream SCIM provisioning behavior.")
    parser.add_argument("--config", default="config.json", help="Path to config JSON file.")
    parser.add_argument("--operation", choices=["test", "discovery"], help="Override operation from config.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Create a dry-run report without sending SCIM requests.")
    mode.add_argument("--apply", action="store_true", help="Execute SCIM requests. Required for mutation testing.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        if args.operation:
            # Re-read config immutably by replacing field through object copy would be overkill here.
            from dataclasses import replace
            config = replace(config, operation=args.operation)
            if args.operation == "discovery":
                adjusted = dict(config.operations)
                for key in ["createUser", "updateUser", "deactivateUser", "createGroup", "groupPush", "cleanup"]:
                    adjusted[key] = False
                config = replace(config, operations=adjusted)

        plan = load_test_plan(config.plan_file)
        plan_operations = build_plan(config.operations, plan)
        if args.dry_run:
            output_dir = write_dry_run(config, plan_operations, args.config)
        else:
            if config.operation == "test" and not args.apply:
                output_dir = write_dry_run(config, plan_operations, args.config)
            else:
                output_dir = execute_plan(config, plan_operations, args.config, apply=args.apply)
        print(f"Output written to: {output_dir}")
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI must show clean failure
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
