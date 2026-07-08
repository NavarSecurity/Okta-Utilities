from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .analyzer import analyze
from .config import ConfigError, load_config
from .reports import create_output_dir, write_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze Okta groups for cleanup review candidates.")
    parser.add_argument("--config", default="input/group-cleanup-analyzer.config.json", help="Path to config JSON/YAML file.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Build analysis plan without reading Okta or writing findings.")
    mode.add_argument("--analyze", action="store_true", help="Run group cleanup analysis.")
    parser.add_argument("--print-json", action="store_true", help="Print result JSON to stdout.")
    parser.add_argument("--version", action="version", version=f"okta-group-cleanup-analyzer {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    dry_run = args.dry_run or not args.analyze
    try:
        config = load_config(args.config)
        result = analyze(config, dry_run=dry_run)
        out_dir = create_output_dir(config.get("outputDir", "output"))
        write_outputs(out_dir, result, dry_run=dry_run)
        result["outputDir"] = str(out_dir)
        if args.print_json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            action = "Dry-run plan" if dry_run else "Analysis"
            print(f"{action} complete. Output: {out_dir}")
        strict = bool(config.get("settings", {}).get("strictMode", False))
        if strict and not dry_run and result.get("candidateCount", 0) > 0:
            return 1
        return 0
    except (ConfigError, FileNotFoundError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover
        print(f"Runtime error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
