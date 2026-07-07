from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VALID_ACTIONS = {"add", "remove", "replace"}


@dataclass
class MembershipRequest:
    row_number: int
    action: str
    group_id: str = ""
    group_name: str = ""
    user_id: str = ""
    login: str = ""
    email: str = ""
    approved: str = ""
    reason: str = ""
    source: dict[str, Any] = field(default_factory=dict)

    @property
    def user_lookup_value(self) -> str:
        return self.user_id or self.login or self.email

    @property
    def group_lookup_value(self) -> str:
        return self.group_id or self.group_name

    def normalized_action(self) -> str:
        return (self.action or "").strip().lower()


@dataclass
class PlannedChange:
    row_number: int
    action: str
    group_id: str
    group_name: str
    user_id: str
    login: str
    email: str
    reason: str
    status: str = "planned"
    message: str = ""
    rollback_method: str = ""
    rollback_endpoint: str = ""


@dataclass
class SkippedRecord:
    row_number: int
    action: str
    group: str
    user: str
    reason: str


@dataclass
class FailedRecord:
    row_number: int
    action: str
    group: str
    user: str
    error: str
