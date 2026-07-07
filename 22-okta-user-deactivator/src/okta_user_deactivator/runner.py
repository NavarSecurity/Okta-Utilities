from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import AppConfig
from .models import ActionResult, PlanItem
from .okta_client import OktaApiError, OktaClient
from .planner import build_plan, is_blocked_login, read_user_requests
from .reports import write_plan, write_results
from .utils import utc_timestamp, write_json


DEPROVISIONED_STATUSES = {"DEPROVISIONED"}
SUSPENDED_STATUSES = {"SUSPENDED"}


def make_output_dir(base: str | Path) -> Path:
    path = Path(base) / f"okta-user-lifecycle-{utc_timestamp()}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def build_client(config: AppConfig) -> OktaClient:
    return OktaClient(
        org_url=config.target_org_url,
        api_token=config.api_token,
        timeout=config.settings.request_timeout_seconds,
        max_retries=config.settings.max_retries,
    )


def get_profile_login(user: dict[str, Any]) -> str:
    profile = user.get("profile", {}) if isinstance(user, dict) else {}
    return str(profile.get("login") or user.get("login") or "")


def apply_one(item: PlanItem, config: AppConfig, client: OktaClient) -> ActionResult:
    identifier = item.user_id or item.login or item.email
    user = client.get_user(identifier)
    okta_user_id = str(user.get("id", ""))
    current_status = str(user.get("status", ""))
    login = get_profile_login(user) or item.login

    if okta_user_id in config.safety.blocked_user_ids:
        return ActionResult(item.row_number, identifier, okta_user_id, login, item.action, current_status, current_status, False, True, "User ID is blocked by safety configuration.")
    if is_blocked_login(login, config.safety.blocked_login_patterns):
        return ActionResult(item.row_number, identifier, okta_user_id, login, item.action, current_status, current_status, False, True, "Resolved login matched blocked login pattern.")
    if config.safety.prevent_self_deactivation_login and login.lower() == config.safety.prevent_self_deactivation_login.lower():
        return ActionResult(item.row_number, identifier, okta_user_id, login, item.action, current_status, current_status, False, True, "Resolved login matches preventSelfDeactivationLogin.")

    if config.settings.skip_already_in_target_state:
        if item.action == "suspend" and current_status in SUSPENDED_STATUSES:
            return ActionResult(item.row_number, identifier, okta_user_id, login, item.action, current_status, current_status, True, True, "User is already suspended.")
        if item.action == "deprovision" and current_status in DEPROVISIONED_STATUSES:
            return ActionResult(item.row_number, identifier, okta_user_id, login, item.action, current_status, current_status, True, True, "User is already deprovisioned.")

    if item.action == "suspend":
        response = client.suspend_user(okta_user_id)
        return ActionResult(
            item.row_number,
            identifier,
            okta_user_id,
            login,
            item.action,
            current_status,
            "SUSPENDED",
            True,
            False,
            "User suspend request completed.",
            rollback_action="unsuspend",
            rollback_endpoint=f"POST /api/v1/users/{okta_user_id}/lifecycle/unsuspend",
            okta_response=response,
        )

    if item.action == "deprovision":
        response = client.deactivate_user(okta_user_id, send_email=config.settings.send_deprovision_email)
        return ActionResult(
            item.row_number,
            identifier,
            okta_user_id,
            login,
            item.action,
            current_status,
            "DEPROVISIONED",
            True,
            False,
            "User deprovision request completed.",
            rollback_action="activate",
            rollback_endpoint=f"POST /api/v1/users/{okta_user_id}/lifecycle/activate?sendEmail=false",
            okta_response=response,
        )

    if item.action == "delete":
        if config.settings.require_deprovisioned_before_delete and current_status not in DEPROVISIONED_STATUSES:
            return ActionResult(
                item.row_number,
                identifier,
                okta_user_id,
                login,
                item.action,
                current_status,
                current_status,
                False,
                True,
                "Delete skipped because the user is not DEPROVISIONED. Deprovision the user first or set requireDeprovisionedBeforeDelete=false.",
            )
        response = client.delete_user(okta_user_id, send_email=config.settings.send_delete_email)
        return ActionResult(
            item.row_number,
            identifier,
            okta_user_id,
            login,
            item.action,
            current_status,
            "DELETED",
            True,
            False,
            "User delete request completed.",
            rollback_action="",
            rollback_endpoint="",
            okta_response=response,
        )

    raise ValueError(f"Unsupported action: {item.action}")


def dry_run_verify(item: PlanItem, client: OktaClient) -> ActionResult:
    identifier = item.user_id or item.login or item.email
    user = client.get_user(identifier)
    okta_user_id = str(user.get("id", ""))
    current_status = str(user.get("status", ""))
    login = get_profile_login(user) or item.login
    return ActionResult(
        row_number=item.row_number,
        identifier=identifier,
        okta_user_id=okta_user_id,
        login=login,
        action=item.action,
        previous_status=current_status,
        result_status=current_status,
        success=True,
        skipped=True,
        message="Dry-run verification resolved user in Okta. No action taken.",
    )


def run(config: AppConfig, mode: str, confirmation_phrase: str = "") -> Path:
    if mode not in {"dry-run", "apply"}:
        raise ValueError("mode must be dry-run or apply")
    if mode == "apply" and config.safety.require_confirmation_phrase_for_apply:
        if confirmation_phrase != config.safety.confirmation_phrase:
            raise ValueError(
                "Apply mode requires the configured confirmation phrase. "
                f"Expected: {config.safety.confirmation_phrase!r}"
            )

    output_dir = make_output_dir(config.output_dir)
    requests = read_user_requests(config.input_file, config)
    plan = build_plan(requests, config)
    write_plan(output_dir, plan)
    write_json(output_dir / "run_metadata.json", {
        "mode": mode,
        "targetOrgUrl": config.target_org_url,
        "inputFile": config.input_file,
        "outputDir": str(output_dir),
        "verifyUsersOnDryRun": config.settings.verify_users_on_dry_run,
        "allowDeleteDeprovisionedUsers": config.settings.allow_delete_deprovisioned_users,
        "requireDeprovisionedBeforeDelete": config.settings.require_deprovisioned_before_delete,
    })

    results: list[ActionResult] = []
    errors: list[str] = []
    client: OktaClient | None = None
    if mode == "apply" or config.settings.verify_users_on_dry_run:
        client = build_client(config)

    for item in plan:
        if not item.planned:
            results.append(ActionResult(item.row_number, item.identifier, item.user_id, item.login, item.action, "", "", False, True, item.message))
            continue
        try:
            if mode == "dry-run":
                if client:
                    results.append(dry_run_verify(item, client))
                else:
                    results.append(ActionResult(item.row_number, item.identifier, item.user_id, item.login, item.action, "", "", True, True, "Dry-run only. No Okta action taken."))
            else:
                assert client is not None
                results.append(apply_one(item, config, client))
        except OktaApiError as exc:
            message = f"Row {item.row_number} {item.identifier}: {exc}; response={exc.response}"
            errors.append(message)
            results.append(ActionResult(item.row_number, item.identifier, item.user_id, item.login, item.action, "", "", False, False, message, okta_response=exc.response))
            if not config.settings.continue_on_error:
                break
        except Exception as exc:
            message = f"Row {item.row_number} {item.identifier}: {exc}"
            errors.append(message)
            results.append(ActionResult(item.row_number, item.identifier, item.user_id, item.login, item.action, "", "", False, False, message))
            if not config.settings.continue_on_error:
                break

    write_results(output_dir, mode, plan, results, errors)
    return output_dir
