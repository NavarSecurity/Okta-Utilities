from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import build_config
from .reporting import write_outputs
from .validator import BackupValidator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="okta-backup-validator",
        description="Validate backup folders created by okta-config-backup.",
    )
    parser.add_argument("--config", type=Path, default=None, help="Path to validator config JSON file.")
    parser.add_argument("--backup-dir", type=Path, default=None, help="Backup folder to validate. Overrides config backupDir.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Where validation reports are written. Overrides config outputDir.")
    parser.add_argument("--strict", action="store_true", help="Fail on backup errors, missing files, or warnings.")
    parser.add_argument("--fail-on-warnings", action="store_true", help="Return a failing exit code when warnings are present.")
    parser.add_argument("--print-json", action="store_true", help="Print validation_result.json content to stdout.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        cfg = build_config(
            args.config,
            cli_backup_dir=args.backup_dir,
            cli_output_dir=args.output_dir,
            cli_strict=args.strict,
            cli_fail_on_warnings=args.fail_on_warnings,
        )
        result = BackupValidator(cfg).run()
        outputs = write_outputs(cfg.output_dir, result)

        if args.print_json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"Validation complete: {outputs['run_dir']}")
            print(f"Result: {outputs['result']}")
            print(f"Report: {outputs['report']}")
            print(f"Overall status: {result['overallStatus']}")

        
        if result["overallStatus"] == "FAIL":
            return 1
        if result["overallStatus"] == "WARN" and cfg.fail_on_warnings:
            return 1
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI should give a clear failure instead of traceback by default.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
