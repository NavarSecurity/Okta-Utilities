from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import AppConfig, GroupRuleConfig
from .okta_client import OktaApiError, OktaClient
from .payloads import build_group_rule_payload
from .reports import write_csv, write_execution_report, write_json


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _rule_should_activate(config: AppConfig, rule: GroupRuleConfig) -> bool:
    if rule.activate is not None:
        return rule.activate
    return config.settings.activate_after_create


def _base_plan_entry(rule: GroupRuleConfig, target_group_ids: list[str], unresolved_group_names: list[str]) -> dict[str, Any]:
    return {
        "ruleName": rule.name,
        "approved": rule.approved,
        "expression": rule.expression,
        "conditionSource": rule.condition_source,
        "basicCondition": rule.basic_condition,
        "targetGroupIds": target_group_ids,
        "targetGroupNames": rule.target_group_names,
        "unresolvedTargetGroupNames": unresolved_group_names,
        "excludeUserIds": rule.exclude_user_ids,
        "excludeGroupIds": rule.exclude_group_ids,
        "description": rule.description,
    }


def _resolve_target_groups(client: OktaClient | None, rule: GroupRuleConfig, apply: bool) -> tuple[list[str], list[dict[str, Any]], list[str]]:
    target_group_ids = list(dict.fromkeys(rule.target_group_ids))
    resolved_groups: list[dict[str, Any]] = []
    unresolved_names: list[str] = []

    for group_name in rule.target_group_names:
        if not apply or client is None:
            unresolved_names.append(group_name)
            continue
        group = client.find_group_by_exact_name(group_name)
        group_id = str(group.get("id"))
        if group_id and group_id not in target_group_ids:
            target_group_ids.append(group_id)
        resolved_groups.append({
            "name": group_name,
            "id": group_id,
        })

    return target_group_ids, resolved_groups, unresolved_names


def run(config: AppConfig, *, apply: bool, output_dir: str | Path = "output") -> dict[str, Any]:
    mode = "apply" if apply else "dry-run"
    run_folder = Path(output_dir) / f"okta-group-rule-create-{_timestamp()}"
    run_folder.mkdir(parents=True, exist_ok=True)

    client = None
    if apply:
        client = OktaClient(
            config.target_org_url,
            config.api_token,
            timeout=config.settings.request_timeout_seconds,
            max_retries=config.settings.max_retries,
        )

    plan: list[dict[str, Any]] = []
    created: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    rollback: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    warnings: list[str] = []
    activated_count = 0

    for rule in config.rules:
        try:
            activate_rule = _rule_should_activate(config, rule)
            if config.settings.require_approved and not rule.approved:
                skipped.append({
                    "ruleName": rule.name,
                    "reason": "Rule was not approved for creation.",
                    "action": "skip",
                })
                continue

            target_group_ids, resolved_groups, unresolved_names = _resolve_target_groups(client, rule, apply)
            plan_entry = _base_plan_entry(rule, target_group_ids, unresolved_names)
            plan_entry.update({
                "activateAfterCreate": activate_rule,
                "resolvedGroups": resolved_groups,
                "operation": "create_group_rule",
            })

            if apply and not target_group_ids:
                raise OktaApiError("No target groups were resolved for rule.")

            payload_group_ids = target_group_ids if apply else target_group_ids or [f"RESOLVE_BY_NAME:{name}" for name in unresolved_names]
            payload = build_group_rule_payload(rule, payload_group_ids)
            plan_entry["payload"] = payload
            plan.append(plan_entry)

            if not apply:
                continue

            assert client is not None
            existing = client.find_group_rule_by_name(rule.name)
            if existing and config.settings.skip_existing:
                skipped.append({
                    "ruleName": rule.name,
                    "reason": "Existing group rule found and skipExisting is enabled.",
                    "existingRuleId": existing.get("id", ""),
                    "action": "skip",
                })
                continue

            created_rule = client.create_group_rule(payload)
            rule_id = str(created_rule.get("id", ""))
            activated = False
            if activate_rule and rule_id:
                client.activate_group_rule(rule_id)
                activated = True
                activated_count += 1

            created.append({
                "ruleName": rule.name,
                "ruleId": rule_id,
                "status": "ACTIVE" if activated else created_rule.get("status", "INACTIVE"),
                "activated": str(activated).lower(),
                "targetGroupIds": ";".join(target_group_ids),
            })
            if rule_id:
                rollback.append({
                    "ruleName": rule.name,
                    "ruleId": rule_id,
                    "operation": "delete_group_rule",
                    "method": "DELETE",
                    "endpoint": f"/api/v1/groups/rules/{rule_id}",
                    "note": "Deactivate rule before deletion if Okta requires it.",
                })

        except Exception as exc:  # noqa: BLE001 - report and optionally continue
            message = str(exc)
            if isinstance(exc, OktaApiError) and exc.response_body is not None:
                message = f"{message} | status={exc.status_code} | response={exc.response_body}"
            failed.append({
                "ruleName": rule.name,
                "reason": message,
                "action": "failed",
            })
            errors.append({
                "ruleName": rule.name,
                "message": message,
            })
            if not config.settings.continue_on_error:
                break

    result = {
        "mode": mode,
        "targetOrgUrl": config.target_org_url,
        "runFolder": str(run_folder),
        "counts": {
            "rulesInConfig": len(config.rules),
            "planned": len(plan),
            "created": len(created),
            "activated": activated_count,
            "skipped": len(skipped),
            "failed": len(failed),
        },
        "created": created,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
        "warnings": warnings,
        "requestSummary": _request_summary(client),
    }

    write_json(run_folder / "group_rule_plan.json", {"mode": mode, "rules": plan})
    write_json(run_folder / "group_rule_create_result.json", result)
    write_json(run_folder / "rollback_plan.json", {"actions": rollback})
    write_csv(run_folder / "created_group_rules.csv", created, ["ruleName", "ruleId", "status", "activated", "targetGroupIds"])
    write_csv(run_folder / "skipped_group_rules.csv", skipped, ["ruleName", "reason", "existingRuleId", "action"])
    write_csv(run_folder / "failed_group_rules.csv", failed, ["ruleName", "reason", "action"])
    write_execution_report(run_folder / "execution_report.md", result)
    return result


def _request_summary(client: OktaClient | None) -> dict[str, Any]:
    if client is None:
        return {"totalRequests": 0, "byStatus": {}}
    by_status: dict[str, int] = {}
    for request in client.requests_made:
        status = str(request.get("status"))
        by_status[status] = by_status.get(status, 0) + 1
    return {
        "totalRequests": len(client.requests_made),
        "byStatus": by_status,
        "requests": client.requests_made,
    }
