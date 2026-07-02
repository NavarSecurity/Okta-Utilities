from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import load_config
from .runner import run_builder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="okta-api-auth-server-builder",
        description="Config-driven Okta custom API authorization server builder.",
    )
    parser.add_argument("--config", required=True, help="Path to API authorization server config JSON file.")
    parser.add_argument("--output-dir", default="output", help="Output directory. Default: output")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Build plan only. This is the default behavior.")
    mode.add_argument("--apply", action="store_true", help="Create objects in Okta.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    apply = bool(args.apply)
    try:
        config = load_config(args.config, require_api_token=apply)
        result = run_builder(config, apply=apply, output_dir=Path(args.output_dir))
        run_dir = Path(args.output_dir) / result["runId"]
        print(f"Run complete: {run_dir}")
        print(f"Mode: {result['mode']}")
        print(f"Errors: {result['summary'].get('errors', 0)}")
        if result["summary"].get("errors", 0):
            print("Review builder_result.json and execution_report.md for details.")
            return 2
        if not apply:
            print("Dry-run only. Re-run with --apply to create objects in Okta.")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
