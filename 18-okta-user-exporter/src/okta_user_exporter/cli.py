from __future__ import annotations

import argparse
import sys

from .config import ConfigError, load_config
from .exporter import UserExporter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export Okta users, profile fields, groups, and app link context.")
    parser.add_argument("--config", default="input/user-export.config.json", help="Path to config JSON file.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Build a plan without calling Okta. Default mode.")
    mode.add_argument("--export", action="store_true", help="Perform read-only export calls against Okta.")
    mode.add_argument("--apply", action="store_true", help="Alias for --export. Kept for toolkit consistency; this utility is read-only.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    export_mode = bool(args.export or args.apply)
    mode_name = "export" if export_mode else "dry-run"
    try:
        config = load_config(args.config, require_token=export_mode)
        runner = UserExporter(config, mode=mode_name)
        if export_mode:
            result = runner.export()
            print(f"Export complete. Output folder: {runner.output_dir}")
            if result.get("errors"):
                print(f"Completed with {len(result['errors'])} error(s). Review the execution report.")
                return 1
            return 0
        runner.dry_run()
        print(f"Dry-run complete. Output folder: {runner.output_dir}")
        return 0
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"Runtime error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
