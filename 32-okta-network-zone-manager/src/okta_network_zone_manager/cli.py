from __future__ import annotations

import argparse
import sys

from .config import load_config, load_dotenv
from .okta_client import OktaClient
from .operations import run_compare, run_export, run_import, run_manage

VALID_OPERATIONS = {"export", "compare", "import", "manage"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="okta-network-zone-manager",
        description="Export, compare, import, and safely manage Okta Network Zones.",
    )
    parser.add_argument("--config", required=True, help="Path to JSON config file.")
    parser.add_argument(
        "--operation",
        choices=sorted(VALID_OPERATIONS),
        help="Operation to run. Overrides config.operation when provided.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Preview mutation operations without changing Okta.")
    mode.add_argument("--apply", action="store_true", help="Apply mutation operations. Required for import/manage changes.")
    parser.add_argument("--env-file", default=".env", help="Path to env file. Default: .env")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        load_dotenv(args.env_file)
        config = load_config(args.config)
        operation = args.operation or config.get("operation") or "export"

        if operation not in VALID_OPERATIONS:
            raise ValueError(f"Unsupported operation: {operation}")

        dry_run = True
        if operation in {"export", "compare"}:
            dry_run = True
        elif args.apply:
            dry_run = False
        elif args.dry_run:
            dry_run = True
        else:
            dry_run = bool(config.get("dryRun", True))

        client = None
        if operation in {"export", "import", "manage"}:
            client = OktaClient.from_config(config)

        if operation == "export":
            result = run_export(config, client)
        elif operation == "compare":
            result = run_compare(config)
        elif operation == "import":
            result = run_import(config, client, dry_run=dry_run)
        elif operation == "manage":
            result = run_manage(config, client, dry_run=dry_run)
        else:  # defensive only
            raise ValueError(f"Unsupported operation: {operation}")

        print(result.console_summary())
        return 0 if not result.has_errors else 2

    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
