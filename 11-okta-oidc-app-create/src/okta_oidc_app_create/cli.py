from __future__ import annotations

import argparse
import sys

from . import __version__
from .config import load_config, validate_runtime
from .runner import run_create


def _split_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create Okta OIDC applications from config.")
    parser.add_argument("--config", default="config.example.json", help="Path to JSON config file.")
    parser.add_argument("--labels", help="Comma-separated app labels to create from the config.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Plan only. Do not create apps. Default mode.")
    mode.add_argument("--apply", action="store_true", help="Create apps and optional assignments.")
    parser.add_argument("--print-json", action="store_true", help="Print result JSON to stdout.")
    parser.add_argument("--version", action="version", version=f"okta-oidc-app-create {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    apply = bool(args.apply)
    try:
        config = load_config(args.config)
        errors = validate_runtime(config, apply=apply)
        if errors:
            for err in errors:
                print(f"ERROR: {err}", file=sys.stderr)
            return 2
        exit_code, run_dir, result = run_create(config, apply=apply, labels=_split_csv(args.labels), print_json=args.print_json)
        print(f"OIDC app create {'apply' if apply else 'dry-run'} complete: {run_dir}")
        print(f"Plan: {run_dir / 'oidc_app_create_plan.json'}")
        print(f"Result: {run_dir / 'oidc_app_create_result.json'}")
        print(f"Report: {run_dir / 'execution_report.md'}")
        if result.get("errors"):
            print(f"Completed with {len(result['errors'])} error(s). Review execution_report.md.")
        return exit_code
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
