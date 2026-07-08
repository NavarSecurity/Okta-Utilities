from __future__ import annotations

import argparse
import sys

from .config import load_config
from .runner import run_export


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export Okta group rules and conditions.")
    parser.add_argument("--config", default="input/group-rule-export.config.json", help="Path to config JSON file.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Validate config and create a planned output folder without calling Okta.")
    mode.add_argument("--export", action="store_true", help="Run the read-only group rule export from Okta.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    mode = "export" if args.export else "dry-run"
    try:
        config = load_config(args.config)
        result = run_export(config, mode)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Mode: {result['mode']}")
    print(f"Run directory: {result['runDirectory']}")
    print(f"Rules exported: {result['rulesExported']}")
    if result.get("errors"):
        print(f"Errors: {len(result['errors'])}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
