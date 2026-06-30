from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .config import GeneratorConfig
from .generator import generate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="okta-hcl-generator",
        description="Generate starter Terraform HCL files from Okta configuration backups.",
    )
    parser.add_argument("--config", help="Path to JSON config file.")
    parser.add_argument("--backup-dir", help="Path to okta-config-backup output folder.")
    parser.add_argument("--output-dir", help="Directory where generated HCL output should be written.")
    parser.add_argument("--include", help="Comma-separated resource types to generate, for example groups,applications.")
    parser.add_argument("--resource-name-prefix", help="Prefix to use for generated Terraform resource names.")
    parser.add_argument("--strict", action="store_true", help="Return failure status when missing files or unsupported resources are found.")
    parser.add_argument("--print-json", action="store_true", help="Print generation result JSON to stdout.")
    parser.add_argument("--version", action="version", version=f"okta-hcl-generator {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        cfg = GeneratorConfig.from_file(args.config)
        cfg.apply_overrides(
            backup_dir=args.backup_dir,
            output_dir=args.output_dir,
            include=args.include,
            resource_name_prefix=args.resource_name_prefix,
            strict=args.strict,
        )
        result = generate(cfg)
        if args.print_json:
            print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        else:
            print(f"HCL generation complete: {result.output_dir}")
            print(f"Plan: {result.output_dir}/hcl_generation_plan.json")
            print(f"Report: {result.output_dir}/hcl_generation_report.md")
            print(f"Status: {result.status}")
        if result.status == "FAIL":
            return 1
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI should convert exceptions to clean messages.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
