from __future__ import annotations

import argparse
import sys

from . import __version__
from .config import load_config
from .runner import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bulk suspend, deprovision, or delete approved Okta users.")
    parser.add_argument("--config", default="input/user-lifecycle.config.json", help="Path to config JSON file.")
    parser.add_argument("--dry-run", action="store_true", help="Create a plan and reports without changing Okta.")
    parser.add_argument("--apply", action="store_true", help="Apply approved lifecycle actions to Okta.")
    parser.add_argument("--confirm", default="", help="Required confirmation phrase for apply mode when enabled in config.")
    parser.add_argument("--version", action="store_true", help="Print utility version and exit.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    if args.apply and args.dry_run:
        parser.error("Use either --dry-run or --apply, not both.")
    mode = "apply" if args.apply else "dry-run"
    try:
        config = load_config(args.config)
        output_dir = run(config, mode=mode, confirmation_phrase=args.confirm)
        print(f"Completed {mode}. Output written to: {output_dir}")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
