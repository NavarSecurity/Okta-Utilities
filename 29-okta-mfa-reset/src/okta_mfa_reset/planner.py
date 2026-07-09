from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple


VALID_ACTIONS = {"reset_all_factors", "delete_factor", "delete_authenticator_enrollment"}
ACTION_ALIASES = {
    "reset": "reset_all_factors",
    "reset_all": "reset_all_factors",
    "reset_all_mfa": "reset_all_factors",
    "reset_factor": "delete_factor",
    "remove_factor": "delete_factor",
    "delete_authenticator": "delete_authenticator_enrollment",
}


@dataclass
class PlannedAction:
    rowNumber: int
    userId: str
    login: str
    email: str
    action: str
    factorId: str = ""
    factorType: str = ""
    provider: str = ""
    authenticatorEnrollmentId: str = ""
    approved: str = ""
    reason: str = ""
    status: str = "planned"
    skipReason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _get(row: Dict[str, str], columns: Dict[str, str], key: str) -> str:
    col = columns.get(key, key)
    return str(row.get(col, "") or "").strip()


def normalize_action(action: str, default_action: str) -> str:
    value = (action or default_action or "reset_all_factors").strip().lower()
    return ACTION_ALIASES.get(value, value)


def is_approved(value: str, approved_values: List[str]) -> bool:
    return value.strip().lower() in {v.lower() for v in approved_values}


def is_protected_login(login: str, email: str, patterns: List[str]) -> bool:
    target = f"{login} {email}".lower()
    return any(pattern.lower() in target for pattern in patterns if pattern)


def build_plan(rows: List[Dict[str, str]], settings: Dict[str, Any], columns: Dict[str, str]) -> Dict[str, Any]:
    planned: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    approved_count = 0

    approved_values = settings.get("approvedValues", ["true", "yes", "y", "approved"])
    max_users = int(settings.get("maxUsersPerRun", 25))

    for idx, row in enumerate(rows, start=2):
        user_id = _get(row, columns, "userId")
        login = _get(row, columns, "login")
        email = _get(row, columns, "email")
        action = normalize_action(_get(row, columns, "action"), settings.get("defaultAction", "reset_all_factors"))
        factor_id = _get(row, columns, "factorId")
        factor_type = _get(row, columns, "factorType")
        provider = _get(row, columns, "provider")
        enrollment_id = _get(row, columns, "authenticatorEnrollmentId")
        approved = _get(row, columns, "approved")
        reason = _get(row, columns, "reason")

        item = PlannedAction(
            rowNumber=idx,
            userId=user_id,
            login=login,
            email=email,
            action=action,
            factorId=factor_id,
            factorType=factor_type,
            provider=provider,
            authenticatorEnrollmentId=enrollment_id,
            approved=approved,
            reason=reason,
        )

        skip_reason = ""
        if not user_id and not login and not email:
            skip_reason = "Missing user identifier. Provide userId, login, or email."
        elif action not in VALID_ACTIONS:
            skip_reason = f"Unsupported action: {action}"
        elif settings.get("requireApproved", True) and not is_approved(approved, approved_values):
            skip_reason = "User was not approved for MFA reset action."
        elif settings.get("requireReason", True) and not reason:
            skip_reason = "Reason is required."
        elif settings.get("skipProtectedLogins", True) and is_protected_login(login, email, settings.get("protectedLoginPatterns", [])):
            skip_reason = "Login/email matches a protected account pattern."
        elif action == "reset_all_factors" and not settings.get("allowResetAllFactors", True):
            skip_reason = "reset_all_factors is not allowed by config."
        elif action == "delete_factor" and not settings.get("allowDeleteSelectedFactors", True):
            skip_reason = "delete_factor is not allowed by config."
        elif action == "delete_factor" and not factor_id and not factor_type:
            skip_reason = "delete_factor requires factorId or factorType."
        elif action == "delete_authenticator_enrollment" and not settings.get("allowDeleteAuthenticatorEnrollments", False):
            skip_reason = "delete_authenticator_enrollment is not allowed by config."
        elif action == "delete_authenticator_enrollment" and not enrollment_id:
            skip_reason = "delete_authenticator_enrollment requires authenticatorEnrollmentId."

        if skip_reason:
            item.status = "skipped"
            item.skipReason = skip_reason
            skipped.append(item.to_dict())
        else:
            approved_count += 1
            planned.append(item.to_dict())

    if approved_count > max_users:
        marked = []
        for item in planned:
            item = dict(item)
            item["status"] = "skipped"
            item["skipReason"] = f"Approved row count {approved_count} exceeds maxUsersPerRun {max_users}."
            marked.append(item)
        skipped.extend(marked)
        planned = []

    return {
        "summary": {
            "rowsRead": len(rows),
            "plannedActions": len(planned),
            "skippedRows": len(skipped),
            "maxUsersPerRun": max_users,
        },
        "plannedActions": planned,
        "skippedRows": skipped,
    }
