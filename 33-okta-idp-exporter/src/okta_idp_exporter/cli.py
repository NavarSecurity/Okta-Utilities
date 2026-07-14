from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_runtime_config, validate_runtime_config
from .exporter import export_idps


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="okta-idp-exporter",
        description="Export Okta external Identity Provider configuration with secret-safe output.",
    )
    parser.add_argument("--config", required=True, help="Path to config JSON file.")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and write planned actions without calling Okta.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        runtime = load_runtime_config(args.config)
        errors = validate_runtime_config(runtime, require_okta=not args.dry_run)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 2

        run_dir = export_idps(runtime, config_path=str(Path(args.config)), dry_run=args.dry_run)
        print(f"Output written to: {run_dir}")
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI should return a clean error
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
