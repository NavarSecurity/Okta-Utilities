from __future__ import annotations

import argparse
import json
import sys

from .config import load_config
from .importer import UserBulkImporter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bulk import Okta users from CSV with dry-run, duplicate detection, and failure reporting.")
    parser.add_argument("--config", default="input/user-import.config.json", help="Path to JSON config file")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Build an import plan without creating or updating users")
    mode.add_argument("--apply", action="store_true", help="Create/update users in Okta according to the config")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    mode = "apply" if args.apply else "dry-run"
    try:
        cfg = load_config(args.config)
        importer = UserBulkImporter(cfg, mode)
        result = importer.run()
        print(json.dumps({"runId": result["runId"], "mode": result["mode"], "summary": result["summary"]}, indent=2))
        print(f"Output written to: {importer.output_dir}")
        return 1 if result["summary"].get("failedUsers", 0) else 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
