from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any
import json

from .config import InventoryConfig
from .io_utils import read_json, utc_timestamp, write_csv, write_json, write_text
from .normalizers import inventory_rows, load_records, summarize
from .report import build_execution_report, build_inventory_report

RESOURCE_FILES = {
    "org": "org.json",
    "applications": "applications.json",
    "groups": "groups.json",
    "group_rules": "group_rules.json",
    "policies": "policies.json",
    "identity_providers": "identity_providers.json",
    "authorization_servers": "authorization_servers.json",
    "trusted_origins": "trusted_origins.json",
    "network_zones": "network_zones.json",
    "domains": "domains.json",
    "brands": "brands.json",
    "authenticators": "authenticators.json",
    "event_hooks": "event_hooks.json",
    "inline_hooks": "inline_hooks.json",
}


def export_inventory(config: InventoryConfig) -> dict[str, Any]:
    if not config.backup_dir.exists() or not config.backup_dir.is_dir():
        raise FileNotFoundError(f"Backup directory not found: {config.backup_dir}")

    run_id = f"okta-org-inventory-{utc_timestamp()}"
    out_dir = config.output_dir / run_id
    inventory: dict[str, Any] = {
        "utility": "okta-org-inventory-exporter",
        "version": "0.1.0",
        "runId": run_id,
        "sourceBackupDir": str(config.backup_dir),
        "outputDir": str(out_dir),
        "config": _config_for_output(config),
        "manifest": None,
        "summary": {"totalRecords": 0, "resources": {}},
        "resources": {},
        "warnings": [],
        "errors": [],
    }

    manifest = _load_manifest(config.backup_dir, inventory)
    inventory["manifest"] = manifest
    if manifest and isinstance(manifest.get("errors"), list) and manifest["errors"]:
        msg = f"Source backup manifest contains {len(manifest['errors'])} recorded error(s)."
        if config.fail_on_manifest_errors:
            inventory["errors"].append({"code": "MANIFEST_ERRORS_PRESENT", "message": msg})
        else:
            inventory["warnings"].append({"code": "MANIFEST_ERRORS_PRESENT", "message": msg})

    for resource in config.include:
        filename = RESOURCE_FILES.get(resource)
        if not filename:
            inventory["warnings"].append({"code": "UNKNOWN_RESOURCE", "resource": resource, "message": f"Unsupported resource requested: {resource}"})
            continue
        path = config.backup_dir / filename
        if not path.exists():
            inventory["warnings"].append({"code": "MISSING_FILE", "resource": resource, "file": filename, "message": f"Backup file not found: {filename}"})
            inventory["resources"][resource] = {"count": 0, "records": [], "rows": []}
            inventory["summary"]["resources"][resource] = {"count": 0, "missing": True}
            continue
        try:
            raw = read_json(path)
            records = load_records(resource, raw)
            rows, fieldnames = inventory_rows(resource, records)
            resource_summary = summarize(records, "policyType" if resource == "policies" else "type")
            inventory["resources"][resource] = {
                "file": filename,
                "count": len(records),
                "summary": resource_summary,
                "rows": rows,
                "fieldnames": fieldnames,
            }
            inventory["summary"]["resources"][resource] = resource_summary
            inventory["summary"]["totalRecords"] += len(records)
        except json.JSONDecodeError as exc:
            inventory["errors"].append({"code": "INVALID_JSON", "resource": resource, "file": filename, "message": str(exc)})
        except Exception as exc:  # defensive reporting for odd backup structures
            inventory["errors"].append({"code": "RESOURCE_PARSE_ERROR", "resource": resource, "file": filename, "message": str(exc)})

    if config.strict_mode and inventory["warnings"]:
        inventory["errors"].append({
            "code": "STRICT_MODE_WARNINGS",
            "message": f"Strict mode is enabled and {len(inventory['warnings'])} warning(s) were found.",
        })

    out_dir.mkdir(parents=True, exist_ok=True)
    if config.write_json:
        write_json(out_dir / "inventory.json", inventory)
    if config.write_markdown:
        write_text(out_dir / "inventory_report.md", build_inventory_report(inventory))
        write_text(out_dir / "execution_report.md", build_execution_report(inventory))
    if config.write_csv:
        csv_dir = out_dir / "csv"
        for resource, details in inventory["resources"].items():
            rows = details.get("rows", [])
            fieldnames = details.get("fieldnames", [])
            if fieldnames:
                write_csv(csv_dir / f"{resource}.csv", rows, fieldnames)

    inventory["outputFiles"] = _list_output_files(out_dir)
    # Rewrite inventory after output file list is known.
    if config.write_json:
        write_json(out_dir / "inventory.json", inventory)
    return inventory


def _load_manifest(backup_dir: Path, inventory: dict[str, Any]) -> dict[str, Any] | None:
    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.exists():
        inventory["warnings"].append({"code": "MISSING_MANIFEST", "file": "manifest.json", "message": "Backup manifest not found."})
        return None
    try:
        manifest = read_json(manifest_path)
    except json.JSONDecodeError as exc:
        inventory["errors"].append({"code": "INVALID_MANIFEST_JSON", "file": "manifest.json", "message": str(exc)})
        return None
    if not isinstance(manifest, dict):
        inventory["errors"].append({"code": "INVALID_MANIFEST_SHAPE", "file": "manifest.json", "message": "manifest.json must contain a JSON object."})
        return None
    return {
        "backupId": manifest.get("backupId"),
        "generatedAt": manifest.get("generatedAt"),
        "orgUrl": manifest.get("orgUrl"),
        "requestedResources": manifest.get("requestedResources", []),
        "redactionEnabled": manifest.get("redactionEnabled"),
        "errorCount": len(manifest.get("errors", []) or []),
        "warningCount": len(manifest.get("warnings", []) or []),
    }


def _config_for_output(config: InventoryConfig) -> dict[str, Any]:
    raw = asdict(config)
    raw["backup_dir"] = str(config.backup_dir)
    raw["output_dir"] = str(config.output_dir)
    raw["include"] = list(config.include)
    return raw


def _list_output_files(out_dir: Path) -> list[str]:
    return sorted(str(path.relative_to(out_dir)) for path in out_dir.rglob("*") if path.is_file())
