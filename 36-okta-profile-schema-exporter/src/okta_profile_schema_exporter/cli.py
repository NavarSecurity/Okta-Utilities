from __future__ import annotations

import argparse
import sys

from .config import ConfigError, load_config, validate_runtime_config
from .exporter import export_profile_schemas


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export Okta Universal Directory user and app profile schemas.")
    parser.add_argument("--config", default="config.json", help="Path to configuration JSON file.")
    parser.add_argument("--dry-run", action="store_true", help="Validate configuration and write a dry-run report without calling Okta.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        warnings = validate_runtime_config(config, require_okta=not args.dry_run)
        run_dir = export_profile_schemas(config, dry_run=args.dry_run)
        for warning in warnings:
            print(f"WARNING: {warning}")
        if args.dry_run:
            print(f"Dry-run completed. Report written to: {run_dir}")
        else:
            print(f"Export completed. Output written to: {run_dir}")
        return 0
    except ConfigError as exc:
        print(f"CONFIG ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
