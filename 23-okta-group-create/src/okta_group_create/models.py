from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .config import GroupCreateConfig


class ValidationError(ValueError):
    pass


@dataclass
class GroupSpec:
    row_number: int
    name: str
    description: str = ""
    approved: str | bool | None = None
    profile: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def normalized_name(self) -> str:
        return self.name.strip().lower()


def build_group_specs(rows: list[dict[str, Any]], config: GroupCreateConfig) -> list[GroupSpec]:
    specs: list[GroupSpec] = []
    for index, row in enumerate(rows, start=2):
        profile = _extract_profile(row, config)
        name = str(profile.get("name") or "").strip()
        description = str(profile.get("description") or "").strip()
        approved_column = config.columns.get("approved", "approved")
        approved = row.get(approved_column)
        specs.append(GroupSpec(row_number=index, name=name, description=description, approved=approved, profile=profile, raw=row))
    return specs


def _extract_profile(row: dict[str, Any], config: GroupCreateConfig) -> dict[str, Any]:
    if isinstance(row.get("profile"), dict):
        base = {k: v for k, v in row["profile"].items() if v is not None and str(v).strip() != ""}
    else:
        base = {}

    for okta_profile_field, input_field in config.profile_field_mappings.items():
        value = row.get(input_field)
        if value is None and input_field.startswith("profile."):
            value = row.get(input_field)
        if value is not None and str(value).strip() != "":
            base[okta_profile_field] = str(value).strip()

    # Convenience fallback for common CSV columns.
    if "name" not in base:
        name_col = config.columns.get("name", "name")
        if row.get(name_col):
            base["name"] = str(row.get(name_col)).strip()
    if "description" not in base:
        desc_col = config.columns.get("description", "description")
        if row.get(desc_col):
            base["description"] = str(row.get(desc_col)).strip()
    return base


def validate_specs(specs: list[GroupSpec], config: GroupCreateConfig) -> tuple[list[GroupSpec], list[dict[str, Any]]]:
    valid: list[GroupSpec] = []
    skipped: list[dict[str, Any]] = []
    seen: dict[str, int] = {}

    for spec in specs:
        if not spec.name:
            skipped.append(_skip(spec, "MISSING_NAME", "Group name is required."))
            continue
        key = spec.normalized_name
        if key in seen:
            skipped.append(_skip(spec, "DUPLICATE_INPUT_NAME", f"Duplicate group name in input. First seen on row {seen[key]}."))
            continue
        seen[key] = spec.row_number
        if config.settings.require_approved:
            approved_value = str(spec.approved or "").strip().lower()
            if approved_value not in config.settings.approved_values:
                skipped.append(_skip(spec, "NOT_APPROVED", "Row was not approved for group creation."))
                continue
        valid.append(spec)
    return valid, skipped


def build_group_payload(spec: GroupSpec) -> dict[str, Any]:
    profile = {k: v for k, v in spec.profile.items() if v is not None and str(v).strip() != ""}
    profile["name"] = spec.name
    if spec.description and "description" not in profile:
        profile["description"] = spec.description
    return {"profile": profile}


def _skip(spec: GroupSpec, code: str, reason: str) -> dict[str, Any]:
    return {
        "rowNumber": spec.row_number,
        "name": spec.name,
        "status": "SKIPPED",
        "reasonCode": code,
        "reason": reason,
    }
