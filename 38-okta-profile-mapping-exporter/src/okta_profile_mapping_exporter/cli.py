from __future__ import annotations

import argparse
import sys

from .config import load_config, load_dotenv
from .exporter import run_export


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="okta-profile-mapping-exporter",
        description="Export Okta profile mappings and attribute-level mapping details.",
    )
    parser.add_argument("--config", required=True, help="Path to config JSON file.")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and write a dry-run report without API calls.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        load_dotenv()
        config = load_config(args.config)
        output_dir = run_export(config, config_path=args.config, dry_run=args.dry_run)
        print(f"Completed. Output written to: {output_dir}")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
