from __future__ import annotations

import argparse
import sys

from .config import ConfigError, load_config
from .operations import compare_operation, export_operation, import_operation, validate_operation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export, compare, validate, and import Okta Trusted Origins.")
    parser.add_argument("--config", default="config.json", help="Path to config JSON file. Default: config.json")
    parser.add_argument("--operation", choices=["export", "compare", "validate", "import"], help="Override operation in config file.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Preview mutation operations without applying changes.")
    mode.add_argument("--apply", action="store_true", help="Apply mutation operations.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config, args.operation)
        if config.operation == "export":
            run_dir = export_operation(config)
        elif config.operation == "compare":
            run_dir = compare_operation(config)
        elif config.operation == "validate":
            run_dir = validate_operation(config)
        elif config.operation == "import":
            run_dir = import_operation(config, apply=args.apply)
        else:
            parser.error(f"Unsupported operation: {config.operation}")
            return 2
        print(f"Operation completed: {config.operation}")
        print(f"Output: {run_dir}")
        if config.operation == "import" and not args.apply:
            print("Dry-run mode was used. Review output before running with --apply.")
        return 0
    except (ConfigError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - CLI needs concise failure message
        print(f"Execution failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
