from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class GroupRecord:
    id: str
    name: str
    type: str = ""
    created: str = ""
    last_updated: str = ""
    description: str = ""
    owner: str = ""
    profile: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)
    member_count: int | None = None
    app_assignment_count: int | None = None
    rule_target_count: int | None = None
    duplicate_count: int = 0
    reasons: list[str] = field(default_factory=list)
    recommendation: str = "review"
    is_protected: bool = False
    evidence_notes: list[str] = field(default_factory=list)

    def to_output_row(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "created": self.created,
            "lastUpdated": self.last_updated,
            "description": self.description,
            "owner": self.owner,
            "memberCount": "" if self.member_count is None else self.member_count,
            "appAssignmentCount": "" if self.app_assignment_count is None else self.app_assignment_count,
            "ruleTargetCount": "" if self.rule_target_count is None else self.rule_target_count,
            "duplicateCount": self.duplicate_count,
            "isProtected": str(self.is_protected).lower(),
            "reasonCodes": ";".join(self.reasons),
            "recommendation": self.recommendation,
            "evidenceNotes": ";".join(self.evidence_notes),
        }


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    candidates = [text, text.replace("Z", "+00:00")]
    for candidate in candidates:
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None
