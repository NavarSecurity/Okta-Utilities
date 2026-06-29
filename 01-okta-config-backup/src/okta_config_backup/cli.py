from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import build_config
from .exporter import OktaConfigBackup


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="okta-config-backup",
        description="Export a timestamped, read-only Okta configuration backup.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to JSON config file. Example: input/config.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Override output directory from config file.",
    )
    parser.add_argument(
        "--include",
        default=None,
        help="Comma-separated resource list. Example: applications,groups,policies",
    )
    parser.add_argument(
        "--policy-types",
        default=None,
        help="Comma-separated Okta policy types. Example: OKTA_SIGN_ON,PASSWORD,MFA_ENROLL",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config and print export plan without calling Okta or writing backup data.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"okta-config-backup {__version__}",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        cfg = build_config(
            config_path=args.config,
            cli_output_dir=args.output_dir,
            cli_include=args.include,
            cli_policy_types=args.policy_types,
            dry_run=args.dry_run,
        )
        backup = OktaConfigBackup(cfg)

        if args.dry_run:
            print(json.dumps(backup.dry_run_plan(), indent=2, sort_keys=True))
            return 0

        result = backup.run()
        backup_dir = result["backup_dir"]
        manifest = result["manifest"]
        print(f"Backup complete: {backup_dir}")
        print(f"Manifest: {backup_dir / 'manifest.json'}")
        print(f"Report: {backup_dir / 'execution_report.md'}")
        if manifest.get("errors"):
            print(f"Completed with {len(manifest['errors'])} recorded error(s). Review manifest.json.", file=sys.stderr)
            return 1
        return 0
    except Exception as exc:  # noqa: BLE001 - top-level CLI failure path.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
