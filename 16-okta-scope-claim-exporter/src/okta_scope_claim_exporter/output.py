from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .exporter import ExportResult


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def create_run_dir(output_dir: Path) -> Path:
    run_dir = output_dir / f"okta-scope-claim-exporter-{utc_timestamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def write_plan(run_dir: Path, plan: dict[str, Any]) -> None:
    write_json(run_dir / "scope_claim_export_plan.json", plan)
    write_execution_report(
        run_dir,
        mode="dry-run",
        source_org_url=plan["sourceOrgUrl"],
        summary={
            "authorizationServersExported": 0,
            "authorizationServersSkipped": 0,
            "scopesExported": 0,
            "claimsExported": 0,
            "errors": 0,
        },
        errors=[],
    )


def write_export(run_dir: Path, result: ExportResult) -> None:
    write_json(run_dir / "scope_claim_export.json", result.to_dict())
    write_authorization_servers_csv(run_dir / "authorization_servers.csv", result.authorization_servers)
    write_scopes_csv(run_dir / "scopes.csv", result)
    write_claims_csv(run_dir / "claims.csv", result)
    write_summary_csv(run_dir / "scope_claim_summary.csv", result)
    write_markdown_report(run_dir / "scope_claim_report.md", result)
    write_execution_report(
        run_dir,
        mode=result.mode,
        source_org_url=result.source_org_url,
        summary=result.summary(),
        errors=[e.__dict__ for e in result.errors],
    )
    if result.raw:
        raw_dir = run_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        for name, value in result.raw.items():
            safe_name = name.replace("/", "_").replace(" ", "_")
            write_json(raw_dir / f"{safe_name}.json", value)


def write_authorization_servers_csv(path: Path, servers: list[dict[str, Any]]) -> None:
    fields = ["authorization_server_id", "name", "description", "status", "audiences", "issuer", "issuerMode", "created", "lastUpdated"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for server in servers:
            writer.writerow(
                {
                    "authorization_server_id": server.get("id", ""),
                    "name": server.get("name", ""),
                    "description": server.get("description", ""),
                    "status": server.get("status", ""),
                    "audiences": _join(server.get("audiences")),
                    "issuer": server.get("issuer", ""),
                    "issuerMode": server.get("issuerMode", ""),
                    "created": server.get("created", ""),
                    "lastUpdated": server.get("lastUpdated", ""),
                }
            )


def write_scopes_csv(path: Path, result: ExportResult) -> None:
    server_by_id = {str(s.get("id")): s for s in result.authorization_servers}
    fields = [
        "authorization_server_id",
        "authorization_server_name",
        "scope_id",
        "name",
        "description",
        "status",
        "default",
        "system",
        "consent",
        "metadataPublish",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for server_id, scopes in result.scopes_by_authorization_server_id.items():
            server = server_by_id.get(server_id, {})
            for scope in scopes:
                writer.writerow(
                    {
                        "authorization_server_id": server_id,
                        "authorization_server_name": server.get("name", ""),
                        "scope_id": scope.get("id", ""),
                        "name": scope.get("name", ""),
                        "description": scope.get("description", ""),
                        "status": scope.get("status", ""),
                        "default": scope.get("default", ""),
                        "system": scope.get("system", ""),
                        "consent": scope.get("consent", ""),
                        "metadataPublish": scope.get("metadataPublish", ""),
                    }
                )


def write_claims_csv(path: Path, result: ExportResult) -> None:
    server_by_id = {str(s.get("id")): s for s in result.authorization_servers}
    fields = [
        "authorization_server_id",
        "authorization_server_name",
        "claim_id",
        "name",
        "status",
        "claimType",
        "valueType",
        "value",
        "alwaysIncludeInToken",
        "system",
        "conditions_scopes",
        "conditions_clients",
        "conditions_userType",
        "groupFilterType",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for server_id, claims in result.claims_by_authorization_server_id.items():
            server = server_by_id.get(server_id, {})
            for claim in claims:
                conditions = claim.get("conditions") or {}
                scopes = conditions.get("scopes") or {}
                clients = conditions.get("clients") or {}
                user_type = conditions.get("userType") or {}
                writer.writerow(
                    {
                        "authorization_server_id": server_id,
                        "authorization_server_name": server.get("name", ""),
                        "claim_id": claim.get("id", ""),
                        "name": claim.get("name", ""),
                        "status": claim.get("status", ""),
                        "claimType": claim.get("claimType", ""),
                        "valueType": claim.get("valueType", ""),
                        "value": claim.get("value", ""),
                        "alwaysIncludeInToken": claim.get("alwaysIncludeInToken", ""),
                        "system": claim.get("system", ""),
                        "conditions_scopes": _join(scopes.get("include") if isinstance(scopes, dict) else scopes),
                        "conditions_clients": _join(clients.get("include") if isinstance(clients, dict) else clients),
                        "conditions_userType": _join(user_type.get("include") if isinstance(user_type, dict) else user_type),
                        "groupFilterType": claim.get("group_filter_type", claim.get("groupFilterType", "")),
                    }
                )


def write_summary_csv(path: Path, result: ExportResult) -> None:
    fields = ["authorization_server_id", "authorization_server_name", "status", "scope_count", "claim_count"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for server in result.authorization_servers:
            server_id = str(server.get("id") or "")
            writer.writerow(
                {
                    "authorization_server_id": server_id,
                    "authorization_server_name": server.get("name", ""),
                    "status": server.get("status", ""),
                    "scope_count": len(result.scopes_by_authorization_server_id.get(server_id, [])),
                    "claim_count": len(result.claims_by_authorization_server_id.get(server_id, [])),
                }
            )


def write_markdown_report(path: Path, result: ExportResult) -> None:
    summary = result.summary()
    lines = [
        "# Okta Scope and Claim Export Report",
        "",
        f"Mode: `{result.mode}`",
        f"Source org: `{result.source_org_url}`",
        "",
        "## Summary",
        "",
        f"- Authorization servers exported: {summary['authorizationServersExported']}",
        f"- Authorization servers skipped: {summary['authorizationServersSkipped']}",
        f"- Scopes exported: {summary['scopesExported']}",
        f"- Claims exported: {summary['claimsExported']}",
        f"- Errors: {summary['errors']}",
        "",
        "## Authorization Servers",
        "",
    ]
    if not result.authorization_servers:
        lines.append("No authorization servers exported.")
    else:
        lines.extend(["| Name | ID | Status | Scopes | Claims |", "|---|---|---:|---:|---:|"])
        for server in result.authorization_servers:
            server_id = str(server.get("id") or "")
            lines.append(
                f"| {server.get('name', '')} | `{server_id}` | {server.get('status', '')} | "
                f"{len(result.scopes_by_authorization_server_id.get(server_id, []))} | "
                f"{len(result.claims_by_authorization_server_id.get(server_id, []))} |"
            )
    lines.append("")
    lines.append("## Skipped Authorization Servers")
    lines.append("")
    if not result.skipped_authorization_servers:
        lines.append("None.")
    else:
        lines.extend(["| Name | ID | Status | Reason |", "|---|---|---|---|"])
        for server in result.skipped_authorization_servers:
            lines.append(f"| {server.get('name', '')} | `{server.get('id', '')}` | {server.get('status', '')} | {server.get('reason', '')} |")
    lines.append("")
    lines.append("## Errors")
    lines.append("")
    if not result.errors:
        lines.append("None.")
    else:
        lines.extend(["| Stage | Authorization Server | Status | Message |", "|---|---|---:|---|"])
        for error in result.errors:
            lines.append(
                f"| {error.stage} | {error.authorization_server_name or error.authorization_server_id or ''} | "
                f"{error.status_code or ''} | {str(error.message).replace('|', '/')} |"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_execution_report(run_dir: Path, mode: str, source_org_url: str, summary: dict[str, Any], errors: list[dict[str, Any]]) -> None:
    lines = [
        "# Execution Report",
        "",
        f"Mode: `{mode}`",
        f"Source org: `{source_org_url}`",
        f"Output folder: `{run_dir}`",
        "",
        "## Counts",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Errors")
    lines.append("")
    if not errors:
        lines.append("None.")
    else:
        for error in errors:
            lines.append(f"- {error.get('stage')}: {error.get('message')}")
    (run_dir / "execution_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _join(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ";".join(str(v) for v in value)
    return str(value)
