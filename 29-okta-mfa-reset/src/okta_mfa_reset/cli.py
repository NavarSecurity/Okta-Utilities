from __future__ import annotations

import argparse
import sys

from .config import load_config, ConfigError
from .io_utils import read_csv, ensure_output_dir
from .planner import build_plan
from .okta_client import OktaClient
from .runner import execute_plan
from .reporting import write_reports

CONFIRM_PHRASE = "RESET APPROVED MFA ENROLLMENTS"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reset approved Okta MFA/factor/authenticator enrollments.")
    parser.add_argument("--config", required=True, help="Path to JSON/YAML config file.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Plan actions without changing Okta. Default mode.")
    mode.add_argument("--apply", action="store_true", help="Apply approved MFA reset actions.")
    parser.add_argument("--confirm", default="", help=f"Required confirmation phrase for apply: {CONFIRM_PHRASE}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    apply_mode = bool(args.apply)
    if apply_mode and args.confirm != CONFIRM_PHRASE:
        parser.error(f'Apply mode requires --confirm "{CONFIRM_PHRASE}"')

    try:
        cfg = load_config(args.config)
        rows = read_csv(cfg.users_file)
        plan = build_plan(rows, cfg.settings, cfg.columns)
        output_dir = ensure_output_dir()

        client = OktaClient(
            cfg.org_url,
            cfg.api_token,
            timeout=int(cfg.settings.get("requestTimeoutSeconds", 30)),
            max_retries=int(cfg.settings.get("maxRetries", 3)),
        )
        result = execute_plan(plan, client, cfg.settings, apply=apply_mode)
        write_reports(output_dir, plan, result)

        print(f"Output written to: {output_dir}")
        if result.get("failed"):
            print(f"Completed with {len(result['failed'])} failure(s).")
            return 2
        return 0
    except (ConfigError, FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
