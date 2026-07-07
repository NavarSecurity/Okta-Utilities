from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .config import AppConfig, normalize_action
from .models import PlanItem, UserRequest
from .utils import truthy

VALID_ACTIONS = {"suspend", "deprovision", "delete"}


def read_user_requests(input_file: str | Path, config: AppConfig) -> list[UserRequest]:
    path = Path(input_file)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    requests: list[UserRequest] = []
    c = config.columns
    for index, row in enumerate(rows, start=2):
        raw_action = (row.get(c.action) or config.settings.default_action or "suspend").strip().lower()
        action_value = normalize_action(raw_action)
        approved = truthy(row.get(c.approved), config.settings.approved_values)
        requests.append(UserRequest(
            row_number=index,
            user_id=(row.get(c.user_id) or "").strip(),
            login=(row.get(c.login) or "").strip(),
            email=(row.get(c.email) or "").strip(),
            action=action_value,
            approved=approved,
            reason=(row.get(c.reason) or "").strip(),
            raw=dict(row),
        ))
    return requests


def is_blocked_login(login: str, patterns: Iterable[str]) -> bool:
    lowered = (login or "").lower()
    return any(pattern and pattern.lower() in lowered for pattern in patterns)


def build_plan(requests: list[UserRequest], config: AppConfig) -> list[PlanItem]:
    plan: list[PlanItem] = []
    if len(requests) > config.settings.max_users_per_run:
        raise ValueError(
            f"Input contains {len(requests)} users, which exceeds maxUsersPerRun={config.settings.max_users_per_run}."
        )
    for req in requests:
        planned = True
        status = "PLANNED"
        message = "Ready for dry-run or apply review."
        identifier = req.identifier

        if not identifier:
            planned = False
            status = "SKIPPED"
            message = "No user identifier was provided. Provide id, login, or email."
        elif req.action not in VALID_ACTIONS:
            planned = False
            status = "SKIPPED"
            message = "Invalid action '{}'. Use suspend, deprovision, deactivate, or delete.".format(req.action)
        elif req.action == "delete" and not config.settings.allow_delete_deprovisioned_users:
            planned = False
            status = "SKIPPED"
            message = "Delete action is disabled. Set settings.allowDeleteDeprovisionedUsers=true to allow deletion of deprovisioned users."
        elif config.settings.require_approved and not req.approved:
            planned = False
            status = "SKIPPED"
            message = "User was not approved for action."
        elif config.settings.require_reason and not req.reason:
            planned = False
            status = "SKIPPED"
            message = "Reason is required."
        elif req.user_id and req.user_id in config.safety.blocked_user_ids:
            planned = False
            status = "SKIPPED"
            message = "User ID is blocked by safety configuration."
        elif req.login and is_blocked_login(req.login, config.safety.blocked_login_patterns):
            planned = False
            status = "SKIPPED"
            message = "Login matched blocked login pattern."
        elif config.safety.prevent_self_deactivation_login and req.login.lower() == config.safety.prevent_self_deactivation_login.lower():
            planned = False
            status = "SKIPPED"
            message = "Login matches preventSelfDeactivationLogin."

        plan.append(PlanItem(
            row_number=req.row_number,
            identifier=identifier,
            user_id=req.user_id,
            login=req.login,
            email=req.email,
            action=req.action,
            approved=req.approved,
            reason=req.reason,
            planned=planned,
            status=status,
            message=message,
        ))
    return plan
