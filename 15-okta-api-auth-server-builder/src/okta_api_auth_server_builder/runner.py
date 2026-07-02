from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .client import OktaApiError, OktaClient
from .config import BuilderConfig
from .payloads import (
    build_authorization_server_payload,
    build_claim_payload,
    build_policy_payload,
    build_policy_rule_payload,
    build_scope_payload,
)
from .reports import write_execution_report
from .util import ensure_dir, rows_to_csv, utc_timestamp, write_json


class _AbortBuild(RuntimeError):
    """Internal control-flow exception used after recording a first actionable error."""


def _find_by_name(items: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    for item in items:
        if item.get("name") == name:
            return item
    return None


def _request_summary(client: Optional[OktaClient]) -> Dict[str, Any]:
    if client is None:
        return {"totalRequests": 0, "byStatus": {}}
    by_status: Dict[str, int] = {}
    for record in client.request_records:
        by_status[str(record.status_code)] = by_status.get(str(record.status_code), 0) + 1
    return {"totalRequests": len(client.request_records), "byStatus": by_status}


def _add_error(errors: List[Dict[str, Any]], item_type: str, name: str, exc: Exception) -> None:
    body = getattr(exc, "response_body", None)
    errors.append(
        {
            "itemType": item_type,
            "name": name,
            "message": str(exc),
            "responseBody": body,
        }
    )


def _rollback_entry(item_type: str, label: str, method: str, path: str) -> Dict[str, Any]:
    return {
        "itemType": item_type,
        "label": label,
        "method": method,
        "path": path,
        "note": "Review before executing. Delete operations can break API authentication flows.",
    }


def run_builder(config: BuilderConfig, apply: bool = False, output_dir: str | Path = "output") -> Dict[str, Any]:
    run_id = f"okta-api-auth-server-builder-{utc_timestamp()}"
    output_path = Path(output_dir) / run_id
    ensure_dir(output_path)

    client = None
    if apply:
        client = OktaClient(
            org_url=config.target_org_url,
            token=config.api_token,
            timeout=config.settings.request_timeout_seconds,
            max_retries=config.settings.max_retries,
        )

    errors: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    rollback: List[Dict[str, Any]] = []
    created_servers: List[Dict[str, Any]] = []
    created_scopes: List[Dict[str, Any]] = []
    created_claims: List[Dict[str, Any]] = []
    created_policies: List[Dict[str, Any]] = []
    created_rules: List[Dict[str, Any]] = []

    plan: Dict[str, Any] = {
        "runId": run_id,
        "mode": "apply" if apply else "dry-run",
        "targetOrgUrl": config.target_org_url,
        "authorizationServers": [],
    }

    existing_servers: List[Dict[str, Any]] = []
    if apply and client:
        existing_servers = client.get_authorization_servers()

    for server in config.authorization_servers:
        server_name = server.get("name", "")
        try:
            server_payload = build_authorization_server_payload(server)
            server_plan = {
                "name": server_name,
                "payload": server_payload,
                "scopes": [],
                "claims": [],
                "policies": [],
            }
            plan["authorizationServers"].append(server_plan)

            server_id = None
            existing_server = _find_by_name(existing_servers, server_name) if apply else None
            if apply and client:
                if existing_server and config.settings.skip_existing:
                    server_id = existing_server.get("id")
                    skipped.append({"itemType": "authorization_server", "name": server_name, "reason": "Already exists"})
                elif existing_server and not config.settings.skip_existing:
                    skipped.append({"itemType": "authorization_server", "name": server_name, "reason": "Already exists; update not supported"})
                    server_id = existing_server.get("id")
                else:
                    created = client.post("/api/v1/authorizationServers", server_payload)
                    server_id = created.get("id")
                    created_servers.append({"name": server_name, "id": server_id, "audiences": ";".join(created.get("audiences", []))})
                    if server_id:
                        rollback.append(_rollback_entry("authorization_server", server_name, "DELETE", f"/api/v1/authorizationServers/{server_id}"))

            # For dry-run we still build child payloads.
            existing_scopes: List[Dict[str, Any]] = []
            existing_claims: List[Dict[str, Any]] = []
            existing_policies: List[Dict[str, Any]] = []
            if apply and client and server_id:
                existing_scopes = client.get_scopes(server_id)
                existing_claims = client.get_claims(server_id)
                existing_policies = client.get_policies(server_id)

            for scope in server.get("scopes", []) or []:
                scope_name = scope.get("name", "")
                try:
                    payload = build_scope_payload(scope, server_name)
                    server_plan["scopes"].append({"name": scope_name, "payload": payload})
                    if apply and client and server_id:
                        existing = _find_by_name(existing_scopes, scope_name)
                        if existing and config.settings.skip_existing:
                            skipped.append({"itemType": "scope", "name": scope_name, "authorizationServer": server_name, "reason": "Already exists"})
                        else:
                            created = client.post(f"/api/v1/authorizationServers/{server_id}/scopes", payload)
                            created_scopes.append({"authorizationServerId": server_id, "authorizationServerName": server_name, "name": scope_name, "id": created.get("id") or created.get("name")})
                            rollback.append(_rollback_entry("scope", f"{server_name}/{scope_name}", "DELETE", f"/api/v1/authorizationServers/{server_id}/scopes/{scope_name}"))
                except Exception as exc:
                    _add_error(errors, "scope", scope_name, exc)
                    if not config.settings.continue_on_error:
                        raise _AbortBuild() from exc

            for claim in server.get("claims", []) or []:
                claim_name = claim.get("name", "")
                try:
                    payload = build_claim_payload(claim, server_name)
                    server_plan["claims"].append({"name": claim_name, "payload": payload})
                    if apply and client and server_id:
                        existing = _find_by_name(existing_claims, claim_name)
                        if existing and config.settings.skip_existing:
                            skipped.append({"itemType": "claim", "name": claim_name, "authorizationServer": server_name, "reason": "Already exists"})
                        else:
                            created = client.post(f"/api/v1/authorizationServers/{server_id}/claims", payload)
                            claim_id = created.get("id")
                            created_claims.append({"authorizationServerId": server_id, "authorizationServerName": server_name, "name": claim_name, "id": claim_id})
                            if claim_id:
                                rollback.append(_rollback_entry("claim", f"{server_name}/{claim_name}", "DELETE", f"/api/v1/authorizationServers/{server_id}/claims/{claim_id}"))
                except Exception as exc:
                    _add_error(errors, "claim", claim_name, exc)
                    if not config.settings.continue_on_error:
                        raise _AbortBuild() from exc

            for policy in server.get("policies", []) or []:
                policy_name = policy.get("name", "")
                policy_id = None
                policy_plan = {"name": policy_name, "payload": {}, "rules": []}
                try:
                    payload = build_policy_payload(policy, server_name)
                    policy_plan["payload"] = payload
                    server_plan["policies"].append(policy_plan)
                    if apply and client and server_id:
                        existing = _find_by_name(existing_policies, policy_name)
                        if existing and config.settings.skip_existing:
                            policy_id = existing.get("id")
                            skipped.append({"itemType": "policy", "name": policy_name, "authorizationServer": server_name, "reason": "Already exists"})
                        else:
                            created = client.post(f"/api/v1/authorizationServers/{server_id}/policies", payload)
                            policy_id = created.get("id")
                            created_policies.append({"authorizationServerId": server_id, "authorizationServerName": server_name, "name": policy_name, "id": policy_id})
                            if policy_id:
                                rollback.append(_rollback_entry("policy", f"{server_name}/{policy_name}", "DELETE", f"/api/v1/authorizationServers/{server_id}/policies/{policy_id}"))

                    existing_rules: List[Dict[str, Any]] = []
                    if apply and client and server_id and policy_id:
                        existing_rules = client.get_policy_rules(server_id, policy_id)

                    for rule in policy.get("rules", []) or []:
                        rule_name = rule.get("name", "")
                        try:
                            rule_payload = build_policy_rule_payload(rule, policy_name)
                            policy_plan["rules"].append({"name": rule_name, "payload": rule_payload})
                            if apply and client and server_id and policy_id:
                                existing_rule = _find_by_name(existing_rules, rule_name)
                                if existing_rule and config.settings.skip_existing:
                                    skipped.append({"itemType": "policy_rule", "name": rule_name, "authorizationServer": server_name, "policy": policy_name, "reason": "Already exists"})
                                else:
                                    created = client.post(f"/api/v1/authorizationServers/{server_id}/policies/{policy_id}/rules", rule_payload)
                                    rule_id = created.get("id")
                                    created_rules.append({"authorizationServerId": server_id, "authorizationServerName": server_name, "policyId": policy_id, "policyName": policy_name, "name": rule_name, "id": rule_id})
                                    if rule_id:
                                        rollback.append(_rollback_entry("policy_rule", f"{server_name}/{policy_name}/{rule_name}", "DELETE", f"/api/v1/authorizationServers/{server_id}/policies/{policy_id}/rules/{rule_id}"))
                        except Exception as exc:
                            _add_error(errors, "policy_rule", rule_name, exc)
                            if not config.settings.continue_on_error:
                                raise _AbortBuild() from exc
                except _AbortBuild:
                    raise
                except Exception as exc:
                    _add_error(errors, "policy", policy_name, exc)
                    if not config.settings.continue_on_error:
                        raise _AbortBuild() from exc

        except _AbortBuild:
            break
        except Exception as exc:
            _add_error(errors, "authorization_server", server_name, exc)
            if not config.settings.continue_on_error:
                break

    summary = {
        "authorizationServersPlanned": len(config.authorization_servers),
        "authorizationServersCreated": len(created_servers),
        "authorizationServersExisting": len([s for s in skipped if s.get("itemType") == "authorization_server"]),
        "scopesCreated": len(created_scopes),
        "scopesExisting": len([s for s in skipped if s.get("itemType") == "scope"]),
        "claimsCreated": len(created_claims),
        "claimsExisting": len([s for s in skipped if s.get("itemType") == "claim"]),
        "policiesCreated": len(created_policies),
        "policiesExisting": len([s for s in skipped if s.get("itemType") == "policy"]),
        "rulesCreated": len(created_rules),
        "rulesExisting": len([s for s in skipped if s.get("itemType") == "policy_rule"]),
        "skipped": len(skipped),
        "errors": len(errors),
    }

    output_files: List[str] = []
    plan_path = output_path / "authorization_server_plan.json"
    write_json(plan_path, plan)
    output_files.append(str(plan_path.name))

    rows_to_csv(output_path / "created_authorization_servers.csv", created_servers, ["name", "id", "audiences"])
    rows_to_csv(output_path / "created_scopes.csv", created_scopes, ["authorizationServerId", "authorizationServerName", "name", "id"])
    rows_to_csv(output_path / "created_claims.csv", created_claims, ["authorizationServerId", "authorizationServerName", "name", "id"])
    rows_to_csv(output_path / "created_policies.csv", created_policies, ["authorizationServerId", "authorizationServerName", "name", "id"])
    rows_to_csv(output_path / "created_policy_rules.csv", created_rules, ["authorizationServerId", "authorizationServerName", "policyId", "policyName", "name", "id"])
    rows_to_csv(output_path / "skipped_items.csv", skipped, ["itemType", "name", "authorizationServer", "policy", "reason"])
    output_files.extend([
        "created_authorization_servers.csv",
        "created_scopes.csv",
        "created_claims.csv",
        "created_policies.csv",
        "created_policy_rules.csv",
        "skipped_items.csv",
    ])

    rollback_path = output_path / "rollback_plan.json"
    write_json(rollback_path, {"runId": run_id, "items": rollback})
    output_files.append("rollback_plan.json")

    result: Dict[str, Any] = {
        "runId": run_id,
        "mode": "apply" if apply else "dry-run",
        "targetOrgUrl": config.target_org_url,
        "summary": summary,
        "requestSummary": _request_summary(client),
        "created": {
            "authorizationServers": created_servers,
            "scopes": created_scopes,
            "claims": created_claims,
            "policies": created_policies,
            "policyRules": created_rules,
        },
        "skipped": skipped,
        "errors": errors,
        "outputFiles": output_files,
    }
    result_path = output_path / "builder_result.json"
    write_json(result_path, result)
    output_files.append("builder_result.json")
    result["outputFiles"] = output_files

    report_path = output_path / "execution_report.md"
    write_execution_report(report_path, result)
    output_files.append("execution_report.md")
    result["outputFiles"] = output_files
    write_json(result_path, result)

    return result
