from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .config import load_config
from .exporter import export_inventory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export readable inventory artifacts from an Okta configuration backup folder.")
    parser.add_argument("--config", help="Path to JSON config file.")
    parser.add_argument("--backup-dir", dest="backupDir", help="Backup folder to inventory.")
    parser.add_argument("--output-dir", dest="outputDir", help="Directory where inventory output should be written.")
    parser.add_argument("--include", help="Comma-separated resource types to include.")
    parser.add_argument("--strict", dest="strictMode", action="store_true", help="Treat warnings as blocking errors.")
    parser.add_argument("--fail-on-manifest-errors", dest="failOnManifestErrors", action="store_true", help="Fail when the source manifest contains recorded API errors.")
    parser.add_argument("--print-json", action="store_true", help="Print the inventory JSON to stdout.")
    parser.add_argument("--version", action="version", version=f"okta-org-inventory-exporter {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    overrides = {
        "backupDir": args.backupDir,
        "outputDir": args.outputDir,
        "include": args.include,
        "strictMode": True if args.strictMode else None,
        "failOnManifestErrors": True if args.failOnManifestErrors else None,
    }
    try:
        config = load_config(args.config, overrides)
        inventory = export_inventory(config)
        if args.print_json:
            print(json.dumps(inventory, indent=2, sort_keys=True))
        status = "FAILED" if inventory.get("errors") else "COMPLETED_WITH_WARNINGS" if inventory.get("warnings") else "COMPLETED"
        print(f"Inventory {status.lower().replace('_', ' ')}: {inventory['outputDir']}")
        print(f"Report: {inventory['outputDir']}/inventory_report.md")
        print(f"Inventory JSON: {inventory['outputDir']}/inventory.json")
        if inventory.get("errors"):
            return 1
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
