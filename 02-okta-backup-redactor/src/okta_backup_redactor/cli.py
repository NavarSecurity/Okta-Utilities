from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .config import load_config
from .runner import run_redaction


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="okta-backup-redactor",
        description="Redact sensitive values from Okta configuration backup folders without modifying the source backup.",
    )
    p.add_argument("--config", help="Path to JSON config file.")
    p.add_argument("--source-backup-dir", help="Backup folder to inspect/redact.")
    p.add_argument("--output-dir", help="Directory where redaction reports and redacted copy are written.")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Plan redactions and write reports only. Does not write redacted backup files. Default mode.")
    mode.add_argument("--apply", action="store_true", help="Write a redacted copy of the source backup into the output folder.")
    p.add_argument("--print-json", action="store_true", help="Print redaction result JSON to stdout.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        cfg = load_config(args.config, source_backup_dir=args.source_backup_dir, output_dir=args.output_dir)
        apply = bool(args.apply)
        result = run_redaction(cfg, apply=apply)
        if args.print_json:
            print(json.dumps(result, indent=2))
        else:
            mode = result["mode"]
            print(f"Redaction {mode} complete: {result['outputDir']}")
            print(f"Report: {result['reportPath']}")
            print(f"Result: {result['resultPath']}")
            if mode == "apply":
                print(f"Redacted backup: {result['redactedBackupDir']}")
            print(f"Findings: {result['summary']['totalFindings']}")

        if cfg.fail_on_findings and result["summary"]["totalFindings"] > 0:
            return 1
        if any(f.get("status") == "error" for f in result.get("files", [])):
            return 1
        return 0
    except Exception as exc:  # noqa: BLE001 - command-line tool
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
