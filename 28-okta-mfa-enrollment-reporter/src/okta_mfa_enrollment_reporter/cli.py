from __future__ import annotations

import argparse
import sys

from .config import ConfigError, load_config
from .runner import run_dry_run, run_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only Okta MFA enrollment reporter")
    parser.add_argument("--config", required=True, help="Path to config JSON file")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Validate config and write a report plan without calling Okta")
    mode.add_argument("--report", action="store_true", help="Run the read-only MFA enrollment report")
    mode.add_argument("--export", action="store_true", help="Alias for --report")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        cfg = load_config(args.config)
        if args.dry_run:
            out = run_dry_run(cfg)
        else:
            out = run_report(cfg)
        print(f"Output written to: {out}")
        return 0
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
