from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

from . import __version__
from .config import load_config, ConfigError
from .runner import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create Okta SAML apps from JSON config with dry-run and evidence output.")
    parser.add_argument("--config", default="config.example.json", help="Path to JSON config file")
    parser.add_argument("--dry-run", action="store_true", help="Plan only; do not create the app")
    parser.add_argument("--apply", action="store_true", help="Create the app in Okta")
    parser.add_argument("--print-json", action="store_true", help="Print result JSON to stdout")
    parser.add_argument("--version", action="version", version=f"okta-saml-app-create {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.apply and args.dry_run:
        parser.error("Use either --dry-run or --apply, not both")

    apply = bool(args.apply)

    try:
        cfg = load_config(Path(args.config))
        result, out_dir = run(cfg, apply=apply)
        if args.print_json:
            print(json.dumps(result, indent=2, sort_keys=True))
        print(f"SAML app create {result.get('mode')} complete: {out_dir}")
        print(f"Plan: {out_dir / 'saml_app_create_plan.json'}")
        print(f"Result: {out_dir / 'saml_app_create_result.json'}")
        print(f"Report: {out_dir / 'execution_report.md'}")
        if result.get("status") in {"ERROR", "CREATED_WITH_ASSIGNMENT_ERRORS"}:
            print(f"Completed with {len(result.get('errors', []))} error(s). Review saml_app_create_result.json.")
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
