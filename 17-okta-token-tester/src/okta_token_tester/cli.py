from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import load_config
from .output import create_run_dir, write_plan, write_results
from .tester import TokenTester


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="okta-token-tester",
        description="Test Okta OIDC/OAuth token flows, JWT validation, JWKS, scopes, claims, and introspection.",
    )
    parser.add_argument("--config", default="config.example.json", help="Path to JSON config file.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Validate config and write a test plan without calling Okta. Default mode.")
    mode.add_argument("--test", action="store_true", help="Run configured read-only token tests against Okta.")
    parser.add_argument("--output-dir", help="Override output directory.")
    parser.add_argument("--print-json", action="store_true", help="Print summary JSON to stdout.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.output_dir:
            config.output_dir = Path(args.output_dir)
        run_dir = create_run_dir(config.output_dir)
        tester = TokenTester(config)
        if args.test:
            result = tester.run_tests()
            write_results(run_dir, result)
            summary = result.summary()
            if args.print_json:
                print(json.dumps({"outputDir": str(run_dir), "summary": summary}, indent=2, sort_keys=True))
            else:
                print(f"Token test complete: {run_dir}")
                print(f"Flows tested: {summary['flowsTested']}")
                print(f"JWT validations: {summary['jwtValidations']}")
                print(f"Introspection tests: {summary['introspectionTests']}")
                print(f"Failed checks: {summary['failedChecks']}")
            return 1 if summary["failedChecks"] else 0
        plan = tester.build_plan()
        write_plan(run_dir, plan)
        if args.print_json:
            print(json.dumps({"outputDir": str(run_dir), "plan": plan}, indent=2, sort_keys=True))
        else:
            print(f"Dry-run complete: {run_dir}")
            print("No Okta API calls were made. Use --test to run configured token tests.")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
