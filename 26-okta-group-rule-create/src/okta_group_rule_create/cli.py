from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .config import ConfigError, load_config
from .runner import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create Okta group rules from configuration.")
    parser.add_argument("--config", default="input/group-rule-create.config.json", help="Path to JSON or YAML config file.")
    parser.add_argument("--output-dir", default="output", help="Output directory. Default: output")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Build a plan without changing Okta. Default behavior.")
    mode.add_argument("--apply", action="store_true", help="Create approved group rules in Okta.")
    parser.add_argument("--print-json", action="store_true", help="Print result JSON to stdout.")
    parser.add_argument("--version", action="version", version=f"okta-group-rule-create {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    apply = bool(args.apply)
    try:
        config = load_config(args.config)
        result = run(config, apply=apply, output_dir=args.output_dir)
        if args.print_json:
            print(json.dumps(result, indent=2, sort_keys=True))
        if result.get("counts", {}).get("failed", 0):
            return 1
        return 0
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"Runtime error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
