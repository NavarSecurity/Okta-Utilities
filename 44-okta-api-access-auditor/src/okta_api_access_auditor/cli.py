from __future__ import annotations

import argparse
import sys

from .config import ConfigError, load_config, load_env
from .exporter import ApiAccessAuditor
from .okta_client import OktaClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit Okta API tokens, OAuth service apps, scopes, admin roles, and overprivileged API access.")
    parser.add_argument("--config", default="config.json", help="Path to config JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and write dry-run evidence without calling Okta export endpoints")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.dry_run:
            org_url = "https://dry-run.example.okta.com"
            api_token = "dry-run-token"
        else:
            org_url, api_token = load_env()
        client = OktaClient(org_url, api_token, timeout_seconds=config.timeout_seconds)
        auditor = ApiAccessAuditor(client, config)
        result = auditor.dry_run() if args.dry_run else auditor.run()
        print(f"Status: {result.get('status')}")
        print(f"Output: {result.get('outputDirectory')}")
        if not args.dry_run:
            print(f"Risk findings: {result.get('riskFindings')}")
            print(f"Request failures: {result.get('requestFailures')}")
        return 0
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
