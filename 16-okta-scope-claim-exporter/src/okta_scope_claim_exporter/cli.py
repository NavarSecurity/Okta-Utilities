from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import load_config
from .exporter import ScopeClaimExporter
from .output import create_run_dir, write_export, write_json, write_plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="okta-scope-claim-exporter",
        description="Read-only exporter for Okta custom authorization server OAuth scopes and claims.",
    )
    parser.add_argument("--config", default="config.example.json", help="Path to JSON config file.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Validate config and write a plan without calling Okta. Default mode.")
    mode.add_argument("--export", action="store_true", help="Perform read-only Okta API export.")
    parser.add_argument("--output-dir", help="Override output directory.")
    parser.add_argument("--print-json", action="store_true", help="Print summary JSON to stdout.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        if args.output_dir:
            config.output_dir = Path(args.output_dir)
        run_dir = create_run_dir(config.output_dir)
        exporter = ScopeClaimExporter(config)

        if args.export:
            result = exporter.export()
            write_export(run_dir, result)
            summary = result.summary()
            if args.print_json:
                print(json.dumps({"outputDir": str(run_dir), "summary": summary}, indent=2, sort_keys=True))
            else:
                print(f"Export complete: {run_dir}")
                print(f"Authorization servers: {summary['authorizationServersExported']}")
                print(f"Scopes: {summary['scopesExported']}")
                print(f"Claims: {summary['claimsExported']}")
                print(f"Errors: {summary['errors']}")
            return 1 if summary["errors"] else 0

        plan = exporter.build_plan()
        write_plan(run_dir, plan)
        if args.print_json:
            print(json.dumps({"outputDir": str(run_dir), "plan": plan}, indent=2, sort_keys=True))
        else:
            print(f"Dry-run complete: {run_dir}")
            print("No Okta API calls were made. Use --export to perform read-only export.")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
