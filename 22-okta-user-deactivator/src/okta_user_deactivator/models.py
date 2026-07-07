from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class UserRequest:
    row_number: int
    user_id: str
    login: str
    email: str
    action: str
    approved: bool
    reason: str
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def identifier(self) -> str:
        return self.user_id or self.login or self.email

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PlanItem:
    row_number: int
    identifier: str
    user_id: str
    login: str
    email: str
    action: str
    approved: bool
    reason: str
    planned: bool
    status: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ActionResult:
    row_number: int
    identifier: str
    okta_user_id: str
    login: str
    action: str
    previous_status: str
    result_status: str
    success: bool
    skipped: bool
    message: str
    rollback_action: str = ""
    rollback_endpoint: str = ""
    okta_response: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
