from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

from . import __version__
from .config import ConfigError, load_config
from .runner import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export Okta app user and group assignments with CSV, JSON, and evidence output.")
    parser.add_argument("--config", default="config.example.json", help="Path to JSON config file")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and write export plan only")
    parser.add_argument("--export", action="store_true", help="Perform read-only Okta API calls and export assignments")
    parser.add_argument("--apply", action="store_true", help="Alias for --export. This utility is read-only and does not modify Okta.")
    parser.add_argument("--print-json", action="store_true", help="Print result JSON to stdout")
    parser.add_argument("--version", action="version", version=f"okta-app-assignment-exporter {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    requested_export = bool(args.export or args.apply)
    if args.dry_run and requested_export:
        parser.error("Use either --dry-run or --export, not both")

    try:
        cfg = load_config(Path(args.config))
        result, out_dir = run(cfg, export=requested_export)
        if args.print_json:
            print(json.dumps(result, indent=2, sort_keys=True))
        print(f"App assignment export {result.get('mode')} complete: {out_dir}")
        print(f"Plan: {out_dir / 'app_assignment_export_plan.json'}")
        print(f"Result: {out_dir / 'app_assignment_export_result.json'}")
        print(f"Report: {out_dir / 'execution_report.md'}")
        if result.get("status") in {"ERROR", "EXPORTED_WITH_ERRORS"}:
            print(f"Completed with {len(result.get('errors', []))} error(s). Review app_assignment_export_result.json.")
            return 1
        return 0
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Runtime error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
