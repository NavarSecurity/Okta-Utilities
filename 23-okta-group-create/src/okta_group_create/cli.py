from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .config import ConfigError, load_config
from .runner import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create Okta groups from CSV, JSON, or YAML input.")
    parser.add_argument("--config", default="input/group-create.config.json", help="Path to config JSON file.")
    parser.add_argument("--dry-run", action="store_true", help="Plan group creation without calling Okta write APIs.")
    parser.add_argument("--apply", action="store_true", help="Create groups in Okta.")
    parser.add_argument("--output-dir", default="output", help="Base output directory.")
    parser.add_argument("--print-json", action="store_true", help="Print result JSON to stdout.")
    parser.add_argument("--version", action="version", version=f"okta-group-create {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.apply and args.dry_run:
        parser.error("Use either --dry-run or --apply, not both.")
    apply_mode = bool(args.apply)
    try:
        config = load_config(args.config)
        result = run(config, apply=apply_mode, output_dir=args.output_dir)
        if args.print_json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"Mode: {result['mode']}")
            print(f"Output: {result['outputDir']}")
            print(f"Planned groups: {result['summary']['plannedGroups']}")
            print(f"Created groups: {result['summary']['createdGroups']}")
            print(f"Skipped groups: {result['summary']['skippedGroups']}")
            print(f"Failed groups: {result['summary']['failedGroups']}")
        return 1 if result.get("errors") else 0
    except (ConfigError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Runtime error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
