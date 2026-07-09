from __future__ import annotations

from typing import Any, Dict, List

from .okta_client import OktaClient, OktaApiError


def _identifier(item: Dict[str, Any]) -> str:
    return item.get("userId") or item.get("login") or item.get("email") or ""


def _summarize_user(user: Dict[str, Any]) -> Dict[str, Any]:
    profile = user.get("profile") or {}
    return {
        "id": user.get("id", ""),
        "status": user.get("status", ""),
        "login": profile.get("login", ""),
        "email": profile.get("email", ""),
    }


def _resolve_factor_id(client: OktaClient, user_id: str, item: Dict[str, Any]) -> str:
    if item.get("factorId"):
        return str(item["factorId"])
    factor_type = str(item.get("factorType") or "").lower()
    provider = str(item.get("provider") or "").lower()
    factors = client.list_factors(user_id)
    matches = []
    for factor in factors:
        if factor_type and str(factor.get("factorType", "")).lower() != factor_type:
            continue
        if provider and str(factor.get("provider", "")).lower() != provider:
            continue
        matches.append(factor)
    if not matches:
        raise OktaApiError(f"No enrolled factor matched factorType={factor_type!r} provider={provider!r}")
    if len(matches) > 1:
        raise OktaApiError(f"Multiple enrolled factors matched factorType={factor_type!r} provider={provider!r}; provide factorId.")
    factor_id = matches[0].get("id")
    if not factor_id:
        raise OktaApiError("Matched factor did not include an id.")
    return str(factor_id)


def execute_plan(plan: Dict[str, Any], client: OktaClient, settings: Dict[str, Any], apply: bool = False) -> Dict[str, Any]:
    changed: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    runtime_skipped: List[Dict[str, Any]] = []

    for item in plan.get("plannedActions", []):
        try:
            user_lookup = _identifier(item)
            if not user_lookup:
                raise OktaApiError("Missing user identifier.")

            user = client.get_user(user_lookup) if settings.get("verifyUsersBeforeAction", True) else {"id": user_lookup, "profile": {"login": item.get("login"), "email": item.get("email")}}
            user_summary = _summarize_user(user)
            user_id = user_summary.get("id") or user_lookup
            action = item.get("action")

            if not apply:
                changed.append({
                    **item,
                    "status": "would_change",
                    "resolvedUserId": user_id,
                    "resolvedLogin": user_summary.get("login", ""),
                    "resolvedUserStatus": user_summary.get("status", ""),
                })
                continue

            if action == "reset_all_factors":
                response = client.reset_all_factors(user_id)
                changed.append({
                    **item,
                    "status": "changed",
                    "resolvedUserId": user_id,
                    "resolvedLogin": user_summary.get("login", ""),
                    "apiAction": f"POST /api/v1/users/{user_id}/lifecycle/reset_factors",
                })
            elif action == "delete_factor":
                factor_id = _resolve_factor_id(client, user_id, item)
                response = client.delete_factor(user_id, factor_id)
                changed.append({
                    **item,
                    "status": "changed",
                    "resolvedUserId": user_id,
                    "resolvedLogin": user_summary.get("login", ""),
                    "resolvedFactorId": factor_id,
                    "apiAction": f"DELETE /api/v1/users/{user_id}/factors/{factor_id}",
                })
            elif action == "delete_authenticator_enrollment":
                enrollment_id = str(item.get("authenticatorEnrollmentId") or "")
                response = client.delete_authenticator_enrollment(user_id, enrollment_id)
                changed.append({
                    **item,
                    "status": "changed",
                    "resolvedUserId": user_id,
                    "resolvedLogin": user_summary.get("login", ""),
                    "apiAction": f"DELETE /api/v1/users/{user_id}/authenticator-enrollments/{enrollment_id}",
                })
            else:
                raise OktaApiError(f"Unsupported action at execution: {action}")
        except Exception as exc:
            failed.append({
                **item,
                "status": "failed",
                "error": str(exc),
                "statusCode": getattr(exc, "status_code", ""),
                "oktaResponse": getattr(exc, "response", ""),
            })
            if not settings.get("continueOnError", False):
                break

    return {
        "summary": {
            "mode": "apply" if apply else "dry-run",
            "changedOrWouldChange": len(changed),
            "failed": len(failed),
            "preSkipped": len(plan.get("skippedRows", [])),
        },
        "changed": changed,
        "skipped": plan.get("skippedRows", []) + runtime_skipped,
        "failed": failed,
    }
