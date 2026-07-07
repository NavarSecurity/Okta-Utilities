from __future__ import annotations

import argparse
import sys

from .config import ConfigError, load_config
from .inputs import InputError
from .runner import RunnerError, run_loader
from .okta_client import OktaApiError

CONFIRM_PHRASE = "APPLY GROUP MEMBERSHIP CHANGES"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bulk load Okta group memberships with dry-run, safety checks, and rollback output.")
    parser.add_argument("--config", required=True, help="Path to group membership loader config JSON")
    parser.add_argument("--dry-run", action="store_true", help="Plan changes without modifying Okta")
    parser.add_argument("--apply", action="store_true", help="Apply approved group membership changes")
    parser.add_argument("--confirm", default="", help=f"Required with --apply. Use: {CONFIRM_PHRASE}")
    parser.add_argument("--output-dir", default="output", help="Base output directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.dry_run and args.apply:
        parser.error("Choose either --dry-run or --apply, not both")
    mode = "apply" if args.apply else "dry-run"
    if mode == "apply" and args.confirm != CONFIRM_PHRASE:
        parser.error(f"--apply requires --confirm \"{CONFIRM_PHRASE}\"")

    try:
        cfg = load_config(args.config)
        run_dir = run_loader(cfg, mode=mode, output_dir=args.output_dir)
        print(f"Okta group membership loader completed in {mode} mode.")
        print(f"Output folder: {run_dir}")
        return 0
    except (ConfigError, InputError, RunnerError, OktaApiError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
