from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .backup import load_applications
from .config import AppClonerConfig
from .sanitizer import app_display_name, app_natural_key, app_type, sanitize_app_for_clone


@dataclass
class CloneOperation:
    source_id: str | None
    label: str
    sign_on_mode: str
    status: str | None
    payload: dict[str, Any]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self, include_payload: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {
            "resource": "applications",
            "sourceId": self.source_id,
            "label": self.label,
            "signOnMode": self.sign_on_mode,
            "sourceStatus": self.status,
            "warnings": self.warnings,
        }
        if include_payload:
            data["payload"] = self.payload
        return data


@dataclass
class ClonePlan:
    operations: list[CloneOperation] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self, include_payload: bool = True) -> dict[str, Any]:
        return {
            "operations": [op.to_dict(include_payload=include_payload) for op in self.operations],
            "skipped": self.skipped,
            "warnings": self.warnings,
            "counts": {
                "operations": len(self.operations),
                "skipped": len(self.skipped),
                "warnings": len(self.warnings),
            },
        }


def _selection(config: AppClonerConfig) -> dict[str, list[str]]:
    apps = (config.selection or {}).get("applications") or {}
    return {
        "labels": [str(x) for x in apps.get("labels", [])],
        "ids": [str(x) for x in apps.get("ids", [])],
        "signOnModes": [str(x) for x in apps.get("signOnModes", [])],
    }


def _selected(app: dict[str, Any], selection: dict[str, list[str]]) -> bool:
    labels = selection["labels"]
    ids = selection["ids"]
    sign_on_modes = selection["signOnModes"]
    if not labels and not ids and not sign_on_modes:
        return True
    if labels and str(app.get("label")) in labels:
        return True
    if ids and str(app.get("id")) in ids:
        return True
    if sign_on_modes and str(app.get("signOnMode")) in sign_on_modes:
        return True
    return False


def build_plan(config: AppClonerConfig) -> ClonePlan:
    apps = load_applications(config.source_backup_dir)
    selection = _selection(config)
    plan = ClonePlan()

    for app in apps:
        label = app_display_name(app)
        source_id = app.get("id")
        status = app.get("status")
        if not _selected(app, selection):
            continue
        if status == "INACTIVE" and not config.clone_inactive_apps:
            plan.skipped.append({
                "resource": "applications",
                "sourceId": source_id,
                "label": label,
                "reason": "source_app_inactive",
            })
            continue
        warnings: list[str] = []
        sign_mode = str(app.get("signOnMode") or "UNKNOWN")
        name = str(app.get("name") or "")
        if sign_mode not in {"OPENID_CONNECT", "SAML_2_0", "BOOKMARK", "BROWSER_PLUGIN", "AUTO_LOGIN"}:
            warnings.append(f"Application signOnMode/name may require manual validation before cloning: {sign_mode or name}")
        if not config.include_assignments:
            warnings.append("Assignments are not cloned by this utility version.")
        if not config.include_provisioning_settings:
            warnings.append("Provisioning settings are intentionally omitted and must be reviewed manually.")
        if app_natural_key(app) == "":
            plan.skipped.append({
                "resource": "applications",
                "sourceId": source_id,
                "label": label,
                "reason": "missing_label_or_name",
            })
            continue
        payload = sanitize_app_for_clone(
            app,
            activate=config.activate_cloned_apps,
            include_provisioning=config.include_provisioning_settings,
        )
        plan.operations.append(CloneOperation(
            source_id=source_id,
            label=label,
            sign_on_mode=sign_mode,
            status=status,
            payload=payload,
            warnings=warnings,
        ))
    return plan
