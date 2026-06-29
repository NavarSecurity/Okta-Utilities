from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import __version__
from .client import OktaApiClient, OktaApiError
from .config import BackupConfig, without_token
from .redaction import redact_sensitive_values
from .resources import RESOURCE_DESCRIPTIONS, SIMPLE_RESOURCES


class OktaConfigBackup:
    def __init__(self, cfg: BackupConfig) -> None:
        self.cfg = cfg
        self.client = OktaApiClient(
            org_url=cfg.org_url,
            api_token=cfg.api_token or "",
            timeout_seconds=cfg.timeout_seconds,
            max_retries=cfg.max_retries,
            retry_base_seconds=cfg.retry_base_seconds,
        )

    def dry_run_plan(self) -> dict[str, Any]:
        return {
            "utility": "okta-config-backup",
            "version": __version__,
            "mode": "dry-run",
            "orgUrl": self.cfg.org_url,
            "outputDir": str(self.cfg.output_dir),
            "include": self.cfg.include,
            "policyTypes": self.cfg.policy_types if "policies" in self.cfg.include else [],
            "redactionEnabled": self.cfg.redaction_enabled,
            "resources": [
                {
                    "name": name,
                    "description": RESOURCE_DESCRIPTIONS.get(name, "No description available."),
                }
                for name in self.cfg.include
            ],
            "note": "Dry run does not call Okta or write backup data.",
        }

    def run(self) -> dict[str, Any]:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_id = f"okta-config-backup-{timestamp}"
        backup_dir = self.cfg.output_dir / backup_id
        backup_dir.mkdir(parents=True, exist_ok=False)

        manifest: dict[str, Any] = {
            "utility": "okta-config-backup",
            "version": __version__,
            "backupId": backup_id,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "orgUrl": self.cfg.org_url,
            "redactionEnabled": self.cfg.redaction_enabled,
            "requestedResources": self.cfg.include,
            "config": serialize_config(without_token(self.cfg)),
            "files": [],
            "counts": {},
            "warnings": [],
            "errors": [],
            "requestSummary": {},
        }

        for resource_name in self.cfg.include:
            try:
                data = self.export_resource(resource_name)
                count = count_objects(data)
                output_data = redact_sensitive_values(data) if self.cfg.redaction_enabled else data
                relative_path = Path(f"{resource_name}.json")
                write_json(backup_dir / relative_path, output_data)
                manifest["files"].append(str(relative_path))
                manifest["counts"][resource_name] = count
            except Exception as exc:  # noqa: BLE001 - CLI records resource-level failures intentionally.
                error_record = exception_to_record(resource_name, exc)
                manifest["errors"].append(error_record)
                if self.cfg.fail_fast:
                    break

        manifest["requestSummary"] = summarize_requests(self.client.request_log)
        write_json(backup_dir / "manifest.json", manifest)
        write_execution_report(backup_dir / "execution_report.md", manifest)
        return {"backup_dir": backup_dir, "manifest": manifest}

    def export_resource(self, resource_name: str) -> Any:
        special_handlers: dict[str, Callable[[], Any]] = {
            "policies": self.export_policies,
            "authorization_servers": self.export_authorization_servers,
        }

        if resource_name in special_handlers:
            return special_handlers[resource_name]()

        resource = SIMPLE_RESOURCES.get(resource_name)
        if not resource:
            raise ValueError(f"Unsupported resource name: {resource_name}")

        if resource.paginated:
            return self.client.get_paginated(resource.path, params={"limit": self.cfg.page_limit})
        return self.client.get_json(resource.path)

    def export_policies(self) -> dict[str, Any]:
        result: dict[str, Any] = {"policyTypes": {}, "warnings": []}

        for policy_type in self.cfg.policy_types:
            type_record: dict[str, Any] = {"policies": [], "rulesByPolicyId": {}, "errors": []}
            try:
                policies = self.client.get_paginated(
                    "/api/v1/policies",
                    params={"type": policy_type, "limit": self.cfg.page_limit},
                )
                type_record["policies"] = policies

                for policy in policies:
                    policy_id = policy.get("id") if isinstance(policy, dict) else None
                    if not policy_id:
                        continue
                    try:
                        rules = self.client.get_paginated(
                            f"/api/v1/policies/{policy_id}/rules",
                            params={"limit": self.cfg.page_limit},
                        )
                        type_record["rulesByPolicyId"][policy_id] = rules
                    except Exception as exc:  # noqa: BLE001
                        type_record["errors"].append(exception_to_record(f"policy_rules:{policy_id}", exc))
            except Exception as exc:  # noqa: BLE001
                type_record["errors"].append(exception_to_record(f"policies:{policy_type}", exc))

            result["policyTypes"][policy_type] = type_record
        return result

    def export_authorization_servers(self) -> dict[str, Any]:
        servers = self.client.get_paginated(
            "/api/v1/authorizationServers",
            params={"limit": self.cfg.page_limit},
        )
        result: dict[str, Any] = {"authorizationServers": servers, "detailsByAuthorizationServerId": {}, "errors": []}

        for server in servers:
            server_id = server.get("id") if isinstance(server, dict) else None
            if not server_id:
                continue

            detail: dict[str, Any] = {
                "scopes": [],
                "claims": [],
                "policies": [],
                "rulesByPolicyId": {},
                "errors": [],
            }

            detail["scopes"] = self.safe_paginated(
                f"authorization_server_scopes:{server_id}",
                f"/api/v1/authorizationServers/{server_id}/scopes",
                params={"limit": self.cfg.page_limit},
                error_sink=detail["errors"],
            )
            detail["claims"] = self.safe_paginated(
                f"authorization_server_claims:{server_id}",
                f"/api/v1/authorizationServers/{server_id}/claims",
                params={"limit": self.cfg.page_limit},
                error_sink=detail["errors"],
            )
            detail["policies"] = self.safe_paginated(
                f"authorization_server_policies:{server_id}",
                f"/api/v1/authorizationServers/{server_id}/policies",
                params={"limit": self.cfg.page_limit},
                error_sink=detail["errors"],
            )

            for policy in detail["policies"]:
                policy_id = policy.get("id") if isinstance(policy, dict) else None
                if not policy_id:
                    continue
                detail["rulesByPolicyId"][policy_id] = self.safe_paginated(
                    f"authorization_server_policy_rules:{server_id}:{policy_id}",
                    f"/api/v1/authorizationServers/{server_id}/policies/{policy_id}/rules",
                    params={"limit": self.cfg.page_limit},
                    error_sink=detail["errors"],
                )

            result["detailsByAuthorizationServerId"][server_id] = detail

        return result

    def safe_paginated(
        self,
        resource_name: str,
        path: str,
        params: dict[str, Any] | None,
        error_sink: list[dict[str, Any]],
    ) -> list[Any]:
        try:
            return self.client.get_paginated(path, params=params)
        except Exception as exc:  # noqa: BLE001
            error_sink.append(exception_to_record(resource_name, exc))
            return []


def serialize_config(cfg: BackupConfig) -> dict[str, Any]:
    data = asdict(cfg)
    data["output_dir"] = str(cfg.output_dir)
    data.pop("api_token", None)
    return data


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")


def count_objects(data: Any) -> int:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        if "authorizationServers" in data and isinstance(data["authorizationServers"], list):
            return len(data["authorizationServers"])
        if "policyTypes" in data and isinstance(data["policyTypes"], dict):
            return sum(
                len(type_record.get("policies", []))
                for type_record in data["policyTypes"].values()
                if isinstance(type_record, dict)
            )
        return 1
    return 0 if data is None else 1


def exception_to_record(resource_name: str, exc: Exception) -> dict[str, Any]:
    if isinstance(exc, OktaApiError):
        return {
            "resource": resource_name,
            "type": "OktaApiError",
            "statusCode": exc.status_code,
            "url": exc.url,
            "message": exc.message,
            "errorBody": redact_sensitive_values(exc.error_body),
        }
    return {"resource": resource_name, "type": exc.__class__.__name__, "message": str(exc)}


def summarize_requests(request_log: list[Any]) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    for item in request_log:
        status = str(item.status_code)
        by_status[status] = by_status.get(status, 0) + 1
    return {
        "totalRequests": len(request_log),
        "byStatus": by_status,
        "totalElapsedSeconds": round(sum(item.elapsed_seconds for item in request_log), 3),
    }


def write_execution_report(path: Path, manifest: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# Okta Configuration Backup Execution Report")
    lines.append("")
    lines.append(f"- Backup ID: `{manifest['backupId']}`")
    lines.append(f"- Generated at: `{manifest['generatedAt']}`")
    lines.append(f"- Org URL: `{manifest['orgUrl']}`")
    lines.append(f"- Redaction enabled: `{manifest['redactionEnabled']}`")
    lines.append("")
    lines.append("## Exported resources")
    lines.append("")
    lines.append("| Resource | Count |")
    lines.append("|---|---:|")
    for resource_name, count in manifest.get("counts", {}).items():
        lines.append(f"| `{resource_name}` | {count} |")
    lines.append("")
    lines.append("## Files")
    lines.append("")
    for file_name in manifest.get("files", []):
        lines.append(f"- `{file_name}`")
    lines.append("")
    lines.append("## API request summary")
    lines.append("")
    request_summary = manifest.get("requestSummary", {})
    lines.append(f"- Total requests: `{request_summary.get('totalRequests', 0)}`")
    lines.append(f"- Total elapsed seconds: `{request_summary.get('totalElapsedSeconds', 0)}`")
    lines.append("- Status counts:")
    for status, count in request_summary.get("byStatus", {}).items():
        lines.append(f"  - `{status}`: {count}")
    lines.append("")
    lines.append("## Errors")
    lines.append("")
    errors = manifest.get("errors", [])
    if not errors:
        lines.append("No resource-level errors were recorded.")
    else:
        for error in errors:
            lines.append(f"- `{error.get('resource')}`: {error.get('type')} - {error.get('message')}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
