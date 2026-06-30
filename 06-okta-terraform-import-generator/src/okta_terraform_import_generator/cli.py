from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from . import __version__
from .generator import TerraformImportGenerator
from .models import GeneratorConfig
from .utils import read_json


def _split_csv(value: str | None) -> List[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def _load_config(path: Path | None) -> Dict[str, Any]:
    if path is None:
        return {}
    return read_json(path)


def _get(config: Dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in config:
            return config[name]
    return default


def build_config(args: argparse.Namespace) -> GeneratorConfig:
    raw = _load_config(Path(args.config)) if args.config else {}
    backup_dir = args.backup_dir or _get(raw, "backupDir", "backup_dir")
    if not backup_dir:
        backup_dir = "input/source-backup"
    output_dir = args.output_dir or _get(raw, "outputDir", "output_dir", default="output")
    include = _split_csv(args.include) if args.include else _get(raw, "include", default=None)
    mode = args.mode or _get(raw, "mode", default="both")
    if mode not in {"commands", "blocks", "both"}:
        raise ValueError("mode must be one of: commands, blocks, both")
    return GeneratorConfig(
        backup_dir=Path(backup_dir),
        output_dir=Path(output_dir),
        include=include or GeneratorConfig(backup_dir=Path(backup_dir)).include,
        mode=mode,
        module_prefix=args.module_prefix if args.module_prefix is not None else _get(raw, "modulePrefix", "module_prefix", default=""),
        resource_name_prefix=args.resource_name_prefix if args.resource_name_prefix is not None else _get(raw, "resourceNamePrefix", "resource_name_prefix", default=""),
        max_resource_name_length=int(_get(raw, "maxResourceNameLength", "max_resource_name_length", default=80)),
        skip_system_objects=bool(args.skip_system_objects or _get(raw, "skipSystemObjects", "skip_system_objects", default=False)),
        strict_mode=bool(args.strict or _get(raw, "strictMode", "strict_mode", default=False)),
        write_csv=bool(_get(raw, "writeCsv", "write_csv", default=True)),
        write_markdown=bool(_get(raw, "writeMarkdown", "write_markdown", default=True)),
        include_unsupported=bool(_get(raw, "includeUnsupported", "include_unsupported", default=True)),
        custom_resource_mappings=_get(raw, "customResourceMappings", "custom_resource_mappings", default={}),
        app_resource_mappings=_get(raw, "appResourceMappings", "app_resource_mappings", default={}),
        idp_resource_mappings=_get(raw, "idpResourceMappings", "idp_resource_mappings", default={}),
        policy_resource_mappings=_get(raw, "policyResourceMappings", "policy_resource_mappings", default={}),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="okta-terraform-import-generator",
        description="Generate Terraform import commands and import blocks from an Okta configuration backup.",
    )
    parser.add_argument("--config", help="Path to JSON config file.")
    parser.add_argument("--backup-dir", "--source-backup-dir", dest="backup_dir", help="Okta backup folder to process.")
    parser.add_argument("--output-dir", help="Directory where generated import artifacts are written.")
    parser.add_argument("--include", help="Comma-separated resource list to include.")
    parser.add_argument("--mode", choices=["commands", "blocks", "both"], help="Output mode: commands, blocks, or both.")
    parser.add_argument("--module-prefix", help="Optional Terraform module address prefix, such as module.okta.")
    parser.add_argument("--resource-name-prefix", help="Optional prefix for generated Terraform resource names.")
    parser.add_argument("--skip-system-objects", action="store_true", help="Skip objects marked system=true.")
    parser.add_argument("--strict", action="store_true", help="Return failure if unsupported resources or warnings are found.")
    parser.add_argument("--print-json", action="store_true", help="Print result JSON to stdout.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    try:
        config = build_config(args)
        result = TerraformImportGenerator(config).generate()
        if args.print_json:
            print(json.dumps(result.__dict__, indent=2, default=str))
        else:
            print(f"Terraform import generation complete: {result.output_dir}")
            print(f"Imports generated: {result.total_imports}")
            print(f"Unsupported objects: {result.total_unsupported}")
            print(f"Status: {result.status}")
        if result.status == "FAIL":
            return 1
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
