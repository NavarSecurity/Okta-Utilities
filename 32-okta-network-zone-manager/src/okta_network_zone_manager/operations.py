from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import load_json_file
from .diff import compare_zones
from .normalize import prepare_zone_payload, summarize_zone, zone_key
from .okta_client import OktaClient
from .reports import RunResult, create_run_dir, finalize_result, write_csv, write_json

DEFAULT_PROTECTED_NAMES = {
    "LegacyIpZone",
    "BlockedIpZone",
    "DefaultEnhancedDynamicZone",
    "DefaultExemptIpZone",
}


def run_export(config: dict[str, Any], client: OktaClient) -> RunResult:
    run_dir = create_run_dir(config.get("outputDir", "output"), "export")
    result = RunResult(operation="export", output_dir=run_dir, dry_run=True)
    export_cfg = config.get("export", {})
    params = {"limit": int(export_cfg.get("limit", 200))}
    if export_cfg.get("filter"):
        params["filter"] = export_cfg["filter"]

    zones = client.paged_get("/api/v1/zones", params=params)
    if not export_cfg.get("includeSystemZones", True):
        zones = [z for z in zones if not z.get("system")]

    result.counts["zones"] = len(zones)
    result.counts["systemZones"] = sum(1 for z in zones if z.get("system"))
    result.counts["customZones"] = sum(1 for z in zones if not z.get("system"))

    full_path = write_json(run_dir / "network_zones_full.json", {"zones": zones})
    summary_rows = [summarize_zone(zone) for zone in zones]
    csv_path = write_csv(run_dir / "network_zones_summary.csv", summary_rows)
    result.add_file(full_path)
    result.add_file(csv_path)
    return finalize_result(result)


def _load_zones_from_file(path: str | Path) -> list[dict[str, Any]]:
    data = load_json_file(path)
    if isinstance(data, dict) and isinstance(data.get("zones"), list):
        return data["zones"]
    if isinstance(data, list):
        return data
    raise ValueError(f"Expected JSON file with a zones array: {path}")


def run_compare(config: dict[str, Any]) -> RunResult:
    run_dir = create_run_dir(config.get("outputDir", "output"), "compare")
    result = RunResult(operation="compare", output_dir=run_dir, dry_run=True)
    compare_cfg = config.get("compare", {})
    source_file = compare_cfg.get("sourceFile")
    target_file = compare_cfg.get("targetFile")
    if not source_file or not target_file:
        raise ValueError("compare.sourceFile and compare.targetFile are required.")

    source_zones = _load_zones_from_file(source_file)
    target_zones = _load_zones_from_file(target_file)
    drift = compare_zones(source_zones, target_zones, match_by=compare_cfg.get("matchBy", "name"))

    drift_payload = {
        "missingInTarget": drift.missing_in_target,
        "extraInTarget": drift.extra_in_target,
        "modified": drift.modified,
        "unchanged": drift.unchanged,
        "summary": {
            "sourceZones": len(source_zones),
            "targetZones": len(target_zones),
            "missingInTarget": len(drift.missing_in_target),
            "extraInTarget": len(drift.extra_in_target),
            "modified": len(drift.modified),
            "unchanged": len(drift.unchanged),
            "totalDifferences": drift.total_differences,
        },
    }
    result.counts = drift_payload["summary"]

    details_path = write_json(run_dir / "zone_drift.json", drift_payload)
    csv_rows = drift_to_csv_rows(drift_payload)
    csv_path = write_csv(run_dir / "zone_drift.csv", csv_rows, fieldnames=["driftType", "zoneName", "matchKey", "field", "source", "target"])
    md_path = write_markdown_drift_report(run_dir / "zone_drift_report.md", drift_payload)

    result.add_file(details_path)
    result.add_file(csv_path)
    result.add_file(md_path)
    return finalize_result(result)


def run_import(config: dict[str, Any], client: OktaClient, *, dry_run: bool) -> RunResult:
    run_dir = create_run_dir(config.get("outputDir", "output"), "import")
    result = RunResult(operation="import", output_dir=run_dir, dry_run=dry_run)
    import_cfg = config.get("import", {})
    input_file = import_cfg.get("inputFile")
    if not input_file:
        raise ValueError("import.inputFile is required.")

    incoming_zones = _load_zones_from_file(input_file)
    current_zones = client.paged_get("/api/v1/zones", params={"limit": 200})
    match_by = import_cfg.get("matchBy", "name")
    current_index = {zone_key(z, match_by): z for z in current_zones}

    protected_names = set(import_cfg.get("protectedNames") or DEFAULT_PROTECTED_NAMES)
    protect_system = bool(import_cfg.get("protectSystemZones", True))
    replace_existing = bool(import_cfg.get("replaceExisting", False))
    activate_created = bool(import_cfg.get("activateCreatedZones", False))

    plan: list[dict[str, Any]] = []
    rollback_actions: list[dict[str, Any]] = []

    for zone in incoming_zones:
        key = zone_key(zone, match_by)
        name = zone.get("name", key)
        existing = current_index.get(key)
        if str(name) in protected_names:
            plan.append(skip_item("protected_name", "Zone name is protected", zone=zone))
            continue
        if existing and protect_system and existing.get("system"):
            plan.append(skip_item("protected_system_zone", "Existing zone is a protected system zone", zone=zone, existing=existing))
            continue
        if not existing:
            payload = prepare_zone_payload(zone, include_status=False)
            plan_item = {"action": "create", "status": "planned", "name": name, "payload": payload}
            plan.append(plan_item)
            if not dry_run:
                created, _ = client.post("/api/v1/zones", payload)
                plan_item["status"] = "applied"
                plan_item["createdId"] = created.get("id") if isinstance(created, dict) else None
                rollback_actions.append({"action": "delete", "match": {"id": plan_item.get("createdId")}, "reason": "Rollback created zone"})
                if activate_created and created and created.get("id"):
                    client.post(f"/api/v1/zones/{created['id']}/lifecycle/activate")
                    rollback_actions.append({"action": "deactivate", "match": {"id": created["id"]}, "reason": "Rollback activation"})
            continue

        if not replace_existing:
            plan.append(skip_item("exists", "Zone already exists and replaceExisting is false", zone=zone, existing=existing))
            continue

        payload = prepare_zone_payload(zone, include_status=False)
        plan_item = {"action": "replace", "status": "planned", "name": name, "targetId": existing.get("id"), "payload": payload}
        plan.append(plan_item)
        rollback_actions.append({"action": "replace", "match": {"id": existing.get("id")}, "zone": prepare_zone_payload(existing, include_status=False), "reason": "Rollback replaced zone"})
        if not dry_run:
            client.put(f"/api/v1/zones/{existing['id']}", payload)
            plan_item["status"] = "applied"

    result.counts = count_plan(plan)
    plan_path = write_json(run_dir / "change_plan.json", {"dryRun": dry_run, "items": plan})
    rollback_path = write_json(run_dir / "rollback_actions.json", {"actions": rollback_actions})
    result.add_file(plan_path)
    result.add_file(rollback_path)
    return finalize_result(result)


def run_manage(config: dict[str, Any], client: OktaClient, *, dry_run: bool) -> RunResult:
    run_dir = create_run_dir(config.get("outputDir", "output"), "manage")
    result = RunResult(operation="manage", output_dir=run_dir, dry_run=dry_run)
    manage_cfg = config.get("manage", {})
    actions_file = manage_cfg.get("actionsFile")
    if not actions_file:
        raise ValueError("manage.actionsFile is required.")
    data = load_json_file(actions_file)
    actions = data.get("actions") if isinstance(data, dict) else None
    if not isinstance(actions, list):
        raise ValueError("Manage actions file must contain an actions array.")

    current_zones = client.paged_get("/api/v1/zones", params={"limit": 200})
    protected_names = set(manage_cfg.get("protectedNames") or DEFAULT_PROTECTED_NAMES)
    protect_system = bool(manage_cfg.get("protectSystemZones", True))
    allow_delete = bool(manage_cfg.get("allowDelete", False))
    allow_delete_active = bool(manage_cfg.get("allowDeleteActiveZones", False))

    plan: list[dict[str, Any]] = []
    rollback_actions: list[dict[str, Any]] = []

    for action in actions:
        action_name = str(action.get("action", "")).lower()
        if action_name not in {"activate", "deactivate", "delete", "create", "replace"}:
            plan.append(skip_item("unsupported_action", f"Unsupported action: {action_name}", action=action))
            continue

        if action_name == "create":
            zone = action.get("zone")
            if not isinstance(zone, dict):
                plan.append(skip_item("invalid_create", "create action requires a zone object", action=action))
                continue
            plan_item = {"action": "create", "status": "planned", "name": zone.get("name"), "payload": prepare_zone_payload(zone, include_status=False)}
            plan.append(plan_item)
            if not dry_run:
                created, _ = client.post("/api/v1/zones", plan_item["payload"])
                plan_item["status"] = "applied"
                plan_item["createdId"] = created.get("id") if isinstance(created, dict) else None
                rollback_actions.append({"action": "delete", "match": {"id": plan_item.get("createdId")}, "reason": "Rollback created zone"})
            continue

        target = find_zone(current_zones, action.get("match") or {})
        if not target:
            plan.append(skip_item("not_found", "No matching zone found", action=action))
            continue

        if target.get("name") in protected_names:
            plan.append(skip_item("protected_name", "Zone name is protected", action=action, target=target))
            continue
        if protect_system and target.get("system"):
            plan.append(skip_item("protected_system_zone", "Target is a protected system zone", action=action, target=target))
            continue

        target_id = target.get("id")
        if not target_id:
            plan.append(skip_item("missing_id", "Target zone has no id", action=action, target=target))
            continue

        if action_name == "replace":
            zone = action.get("zone")
            if not isinstance(zone, dict):
                plan.append(skip_item("invalid_replace", "replace action requires a zone object", action=action))
                continue
            payload = prepare_zone_payload(zone, include_status=False)
            plan_item = {"action": "replace", "status": "planned", "targetId": target_id, "name": target.get("name"), "payload": payload}
            plan.append(plan_item)
            rollback_actions.append({"action": "replace", "match": {"id": target_id}, "zone": prepare_zone_payload(target, include_status=False), "reason": "Rollback replaced zone"})
            if not dry_run:
                client.put(f"/api/v1/zones/{target_id}", payload)
                plan_item["status"] = "applied"
            continue

        if action_name == "delete":
            if not allow_delete:
                plan.append(skip_item("delete_disabled", "Delete is disabled by config", action=action, target=target))
                continue
            if target.get("status") == "ACTIVE" and not allow_delete_active:
                plan.append(skip_item("active_delete_blocked", "Target is ACTIVE and allowDeleteActiveZones is false", action=action, target=target))
                continue
            plan_item = {"action": "delete", "status": "planned", "targetId": target_id, "name": target.get("name")}
            plan.append(plan_item)
            rollback_actions.append({"action": "create", "zone": prepare_zone_payload(target, include_status=False), "reason": "Rollback deleted zone"})
            if not dry_run:
                client.delete(f"/api/v1/zones/{target_id}")
                plan_item["status"] = "applied"
            continue

        lifecycle_path = f"/api/v1/zones/{target_id}/lifecycle/{action_name}"
        plan_item = {"action": action_name, "status": "planned", "targetId": target_id, "name": target.get("name")}
        plan.append(plan_item)
        opposite = "deactivate" if action_name == "activate" else "activate"
        rollback_actions.append({"action": opposite, "match": {"id": target_id}, "reason": f"Rollback {action_name}"})
        if not dry_run:
            client.post(lifecycle_path)
            plan_item["status"] = "applied"

    result.counts = count_plan(plan)
    plan_path = write_json(run_dir / "change_plan.json", {"dryRun": dry_run, "items": plan})
    rollback_path = write_json(run_dir / "rollback_actions.json", {"actions": rollback_actions})
    result.add_file(plan_path)
    result.add_file(rollback_path)
    return finalize_result(result)


def skip_item(reason_code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"action": "skip", "status": "skipped", "reasonCode": reason_code, "message": message, **details}


def count_plan(plan: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"planned": 0, "applied": 0, "skipped": 0, "create": 0, "replace": 0, "activate": 0, "deactivate": 0, "delete": 0}
    for item in plan:
        status = item.get("status")
        action = item.get("action")
        if status in counts:
            counts[status] += 1
        if action in counts:
            counts[action] += 1
    return counts


def find_zone(zones: list[dict[str, Any]], match: dict[str, Any]) -> dict[str, Any] | None:
    if not match:
        return None
    for zone in zones:
        if all(str(zone.get(k, "")).lower() == str(v).lower() for k, v in match.items()):
            return zone
    return None


def drift_to_csv_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in payload["missingInTarget"]:
        source = item.get("source", {})
        rows.append({"driftType": "missing_in_target", "zoneName": source.get("name"), "matchKey": item.get("matchKey"), "field": "", "source": "present", "target": "missing"})
    for item in payload["extraInTarget"]:
        target = item.get("target", {})
        rows.append({"driftType": "extra_in_target", "zoneName": target.get("name"), "matchKey": item.get("matchKey"), "field": "", "source": "missing", "target": "present"})
    for item in payload["modified"]:
        for change in item.get("fieldChanges", []):
            rows.append({"driftType": "modified", "zoneName": item.get("name"), "matchKey": item.get("matchKey"), "field": change.get("field"), "source": change.get("source"), "target": change.get("target")})
    return rows


def write_markdown_drift_report(path: Path, payload: dict[str, Any]) -> Path:
    summary = payload["summary"]
    lines = [
        "# Okta Network Zone Drift Report",
        "",
        "## Summary",
        "",
        f"- Source zones: {summary['sourceZones']}",
        f"- Target zones: {summary['targetZones']}",
        f"- Missing in target: {summary['missingInTarget']}",
        f"- Extra in target: {summary['extraInTarget']}",
        f"- Modified: {summary['modified']}",
        f"- Unchanged: {summary['unchanged']}",
        f"- Total differences: {summary['totalDifferences']}",
        "",
    ]
    if payload["modified"]:
        lines.extend(["## Modified zones", ""])
        for item in payload["modified"]:
            fields = ", ".join(change["field"] for change in item.get("fieldChanges", []))
            lines.append(f"- {item.get('name')} changed fields: {fields}")
        lines.append("")
    if payload["missingInTarget"]:
        lines.extend(["## Missing in target", ""])
        for item in payload["missingInTarget"]:
            lines.append(f"- {item.get('source', {}).get('name', item.get('matchKey'))}")
        lines.append("")
    if payload["extraInTarget"]:
        lines.extend(["## Extra in target", ""])
        for item in payload["extraInTarget"]:
            lines.append(f"- {item.get('target', {}).get('name', item.get('matchKey'))}")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
