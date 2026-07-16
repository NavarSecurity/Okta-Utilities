from __future__ import annotations

import argparse
import sys

from .config import ConfigError, load_config, load_env
from .exporter import dry_run, export_logs
from .okta_client import OktaApiError, OktaClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export Okta System Log events.")
    parser.add_argument("--config", required=True, help="Path to config JSON file.")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and write planned query output without calling Okta.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        cfg = load_config(args.config)
        if args.dry_run:
            run_dir = dry_run(args.config, cfg)
            print(f"Dry-run completed. Output written to: {run_dir}")
            return 0
        org_url, token = load_env()
        client = OktaClient(org_url=org_url, api_token=token, timeout_seconds=cfg.timeout_seconds)
        run_dir = export_logs(args.config, cfg, client)
        print(f"Export completed. Output written to: {run_dir}")
        return 0
    except (ConfigError, OktaApiError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
