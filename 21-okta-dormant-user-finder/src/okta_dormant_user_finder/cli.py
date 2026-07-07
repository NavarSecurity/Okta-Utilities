from __future__ import annotations

import argparse
import sys

from .analyzer import DormantUserFinder
from .config import load_config
from .writer import run_folder, write_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Find stale, never-used, unassigned, or inactive Okta users.")
    parser.add_argument("--config", default="input/dormant-user-finder.config.json", help="Path to config JSON file.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Validate config and write a plan without reading users.")
    mode.add_argument("--find", action="store_true", help="Analyze users and write dormant account reports.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        finder = DormantUserFinder(config)
        result = finder.build_plan() if args.dry_run or not args.find else finder.run()
        out_dir = run_folder()
        write_outputs(result, out_dir)
        print(f"Output written to: {out_dir}")
        if result.get("mode") == "find":
            counts = result.get("counts", {})
            print(f"Users analyzed: {counts.get('usersAnalyzed', 0)}")
            print(f"Dormant candidates: {counts.get('dormantCandidates', 0)}")
        else:
            print("Dry-run plan created. Use --find to analyze users.")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
