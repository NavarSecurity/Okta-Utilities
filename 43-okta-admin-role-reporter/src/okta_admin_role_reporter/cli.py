from __future__ import annotations

import argparse
import sys

from .config import get_okta_settings, load_config
from .exporter import run_export
from .okta_client import OktaClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export Okta admin role assignments and delegated admin access.")
    parser.add_argument("--config", default="config.json", help="Path to config JSON file.")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and create dry-run evidence without calling Okta.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        settings = get_okta_settings(require_credentials=not args.dry_run)
        client = OktaClient(
            org_url=settings.get("org_url", ""),
            token=settings.get("token", ""),
            timeout_seconds=int(config.get("timeoutSeconds", 30)),
        )
        output_dir = run_export(config, client, dry_run=args.dry_run)
        print(f"Output written to: {output_dir}")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
