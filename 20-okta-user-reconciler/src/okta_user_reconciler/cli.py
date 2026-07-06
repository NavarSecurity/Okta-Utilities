from __future__ import annotations

import argparse
import sys

from .config import ConfigError, load_config
from .io_utils import InputError, read_users
from .reconcile import reconcile_users
from .reporting import make_output_dir, write_reports


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reconcile source and target Okta user exports.")
    parser.add_argument("--config", required=True, help="Path to config JSON file")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Validate inputs and generate reconciliation evidence without Okta changes")
    mode.add_argument("--reconcile", action="store_true", help="Run full local reconciliation and generate evidence")
    parser.add_argument("--output-dir", default="output", help="Base output directory")
    return parser


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    mode = "reconcile" if args.reconcile else "dry-run"
    try:
        config = load_config(args.config)
        source_users = read_users(config.source_users_file)
        target_users = read_users(config.target_users_file)
        result = reconcile_users(source_users, target_users, config)
        out_dir = make_output_dir(args.output_dir)
        write_reports(out_dir, config, result, mode)
        print(f"Okta user reconciliation completed in {mode} mode")
        print(f"Output folder: {out_dir}")
        summary = result.get("summary", {})
        print(f"Matched users: {summary.get('matchedUserCount', 0)}")
        print(f"Source-only users: {summary.get('sourceOnlyUserCount', 0)}")
        print(f"Target-only users: {summary.get('targetOnlyUserCount', 0)}")
        print(f"Material differences: {summary.get('materialDifferenceCount', 0)}")
        if config.settings.strict_mode and (
            summary.get("sourceOnlyUserCount", 0)
            or summary.get("targetOnlyUserCount", 0)
            or summary.get("materialDifferenceCount", 0)
            or summary.get("duplicateOrMissingKeyCount", 0)
        ):
            return 1
        return 0
    except (ConfigError, InputError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # defensive CLI boundary
        print(f"ERROR: Unexpected failure: {exc}", file=sys.stderr)
        return 1


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
