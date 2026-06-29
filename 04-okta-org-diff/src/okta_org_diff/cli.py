from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import load_config, merge_cli_overrides, DiffConfig
from .diff_engine import run_diff
from .reporters import make_run_dir, write_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="okta-org-diff",
        description="Compare two Okta configuration backup folders for drift, migration gaps, and post-change differences.",
    )
    parser.add_argument("--config", help="Path to JSON config file.")
    parser.add_argument("--baseline-backup-dir", help="Baseline/source backup folder.")
    parser.add_argument("--comparison-backup-dir", help="Comparison/target backup folder.")
    parser.add_argument("--output-dir", help="Output folder. Default: output")
    parser.add_argument("--include", help="Comma-separated resource list to diff, such as groups,applications,policies.")
    parser.add_argument("--ignore-fields", help="Additional comma-separated fields to ignore during material comparison.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when differences or warnings are detected.")
    parser.add_argument("--fail-on-differences", action="store_true", help="Exit non-zero when any added, removed, changed, or duplicate key differences are found.")
    parser.add_argument("--print-json", action="store_true", help="Print diff_result.json content to stdout.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _config_from_args(args: argparse.Namespace) -> DiffConfig:
    if args.config:
        config = load_config(args.config)
    else:
        if not args.baseline_backup_dir or not args.comparison_backup_dir:
            raise ValueError("Either --config or both --baseline-backup-dir and --comparison-backup-dir are required.")
        config = DiffConfig(
            baseline_backup_dir=Path(args.baseline_backup_dir),
            comparison_backup_dir=Path(args.comparison_backup_dir),
        )
    return merge_cli_overrides(
        config,
        baseline_backup_dir=args.baseline_backup_dir,
        comparison_backup_dir=args.comparison_backup_dir,
        output_dir=args.output_dir,
        include=args.include,
        ignore_fields=args.ignore_fields,
        strict=args.strict,
        fail_on_differences=args.fail_on_differences,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = _config_from_args(args)
        result = run_diff(config)
        run_dir = make_run_dir(config.output_dir)
        written_files = write_outputs(run_dir, result, write_csv=config.write_csv, write_markdown=config.write_markdown)

        if args.print_json:
            print(json.dumps(result, indent=2, sort_keys=True))

        print(f"Org diff complete: {run_dir}")
        print(f"Result: {run_dir / 'diff_result.json'}")
        if config.write_markdown:
            print(f"Report: {run_dir / 'diff_report.md'}")
        print(f"Status: {result['status']}")
        print(f"Added={result['totals']['added']} Removed={result['totals']['removed']} Changed={result['totals']['changed']} Warnings={result['totals']['warnings']} Errors={result['totals']['errors']}")

        should_fail = False
        if result.get("errors"):
            should_fail = True
        if config.fail_on_differences and result.get("hasDifferences"):
            should_fail = True
        if config.strict_mode and (result.get("hasDifferences") or result.get("warnings")):
            should_fail = True
        return 1 if should_fail else 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
