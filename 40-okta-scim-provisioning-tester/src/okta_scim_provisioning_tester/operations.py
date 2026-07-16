from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import AppConfig
from .planner import replace_tokens
from .redact import redact_copy
from .reports import make_output_dir, summarize_results, write_csv, write_json, write_manifest
from .scim_client import ScimClient


class ExecutionError(RuntimeError):
    pass


def _operation_result(operation: dict[str, Any], response: Any, resolved_path: str) -> dict[str, Any]:
    body = response.body if getattr(response, "body", None) is not None else {}
    return {
        "name": operation["name"],
        "method": operation["method"],
        "path": resolved_path,
        "url": response.url,
        "statusCode": response.status_code,
        "ok": response.ok,
        "error": response.error,
        "mutates": operation.get("mutates", False),
        "responseId": body.get("id") if isinstance(body, dict) else None,
        "responseUserName": body.get("userName") if isinstance(body, dict) else None,
        "responseDisplayName": body.get("displayName") if isinstance(body, dict) else None,
    }


def write_dry_run(config: AppConfig, plan_operations: list[dict[str, Any]], config_path: str) -> Path:
    output_dir = make_output_dir(config.output_directory, "scim-provisioning-dry-run")
    planned = redact_copy(plan_operations) if config.redact_sensitive_values else plan_operations
    write_json(output_dir / "planned_operations.json", planned)
    write_json(output_dir / "config_summary.json", {
        "operation": config.operation,
        "baseUrl": config.base_url,
        "authType": config.auth_type,
        "planFile": str(config.plan_file),
        "operationsEnabled": config.operations,
        "cleanup": config.cleanup,
        "httpRequestsWillBeSent": False,
    }, redact_sensitive=config.redact_sensitive_values)
    report = {
        "status": "DRY_RUN",
        "plannedOperations": len(plan_operations),
        "mutatingOperations": sum(1 for item in plan_operations if item.get("mutates") is True),
        "readOnlyOperations": sum(1 for item in plan_operations if item.get("mutates") is False),
    }
    write_json(output_dir / "execution_report.json", report)
    write_manifest(output_dir, config.operation, ["planned_operations.json", "config_summary.json", "execution_report.json", "manifest.json"], config_path)
    return output_dir


def execute_plan(config: AppConfig, plan_operations: list[dict[str, Any]], config_path: str, apply: bool) -> Path:
    if config.operation == "test" and not apply:
        return write_dry_run(config, plan_operations, config_path)

    output_dir = make_output_dir(config.output_directory, f"scim-provisioning-{config.operation}")
    client = ScimClient(config.base_url, config.auth_type, config.timeout_seconds, config.verify_ssl)
    variables: dict[str, str] = {}
    results: list[dict[str, Any]] = []
    responses: list[dict[str, Any]] = []

    for operation in plan_operations:
        requires = operation.get("requires")
        required_values = [requires] if isinstance(requires, str) else (requires or [])
        missing = [key for key in required_values if key not in variables]
        if missing:
            result = {
                "name": operation["name"],
                "method": operation["method"],
                "path": operation["path"],
                "statusCode": None,
                "ok": False,
                "error": f"Skipped because required value(s) are missing: {', '.join(missing)}",
                "mutates": operation.get("mutates", False),
            }
            results.append(result)
            if not config.continue_on_error:
                break
            continue

        resolved_path = replace_tokens(operation["path"], variables)
        payload = replace_tokens(operation.get("payload"), variables) if "payload" in operation else None
        response = client.request(operation["method"], resolved_path, payload)
        result = _operation_result(operation, response, resolved_path)
        results.append(result)
        responses.append({
            "operation": operation["name"],
            "method": operation["method"],
            "path": resolved_path,
            "statusCode": response.status_code,
            "ok": response.ok,
            "body": response.body,
            "error": response.error,
        })

        if response.ok and isinstance(response.body, dict):
            capture = operation.get("captures")
            if capture == "userId" and response.body.get("id"):
                variables["userId"] = str(response.body["id"])
            if capture == "groupId" and response.body.get("id"):
                variables["groupId"] = str(response.body["id"])

        if not response.ok and not config.continue_on_error:
            break

    status = "SUCCESS" if all(item.get("ok") for item in results if item.get("statusCode") is not None) else "COMPLETED_WITH_FAILURES"
    report = summarize_results(results, status)
    report["capturedIds"] = variables

    write_json(output_dir / "operation_results.json", results, redact_sensitive=config.redact_sensitive_values)
    write_json(output_dir / "scim_responses.json", responses, redact_sensitive=config.redact_sensitive_values)
    write_json(output_dir / "execution_report.json", report, redact_sensitive=config.redact_sensitive_values)
    write_csv(output_dir / "operation_results.csv", results, [
        "name", "method", "path", "url", "statusCode", "ok", "error", "mutates", "responseId", "responseUserName", "responseDisplayName"
    ])
    files = ["operation_results.json", "operation_results.csv", "scim_responses.json", "execution_report.json", "manifest.json"]
    write_manifest(output_dir, config.operation, files, config_path)
    return output_dir
