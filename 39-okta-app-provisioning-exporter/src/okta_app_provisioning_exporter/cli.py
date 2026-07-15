from __future__ import annotations

import argparse
import json
import sys

from .config import load_config
from .exporter import dry_run, export


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export Okta app provisioning configuration and related metadata.")
    parser.add_argument("--config", required=True, help="Path to config JSON file.")
    parser.add_argument("--dry-run", action="store_true", help="Validate configuration without calling Okta.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        cfg = load_config(args.config)
        result = dry_run(cfg) if args.dry_run else export(cfg)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
