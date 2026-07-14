from __future__ import annotations

from copy import deepcopy
from typing import Any

from .config import ConfigError

SUPPORTED_TYPES = {"SAML2", "OIDC", "GOOGLE", "FACEBOOK", "APPLE", "MICROSOFT"}


def build_payload(idp_config: dict[str, Any]) -> dict[str, Any]:
    if "payload" in idp_config:
        payload = deepcopy(idp_config["payload"])
    else:
        payload = {
            key: deepcopy(value)
            for key, value in idp_config.items()
            if key not in {"description", "reason", "tags"}
        }

    if not isinstance(payload, dict):
        raise ConfigError("Each identity provider payload must be an object")

    name = idp_config.get("name") or payload.get("name")
    idp_type = idp_config.get("type") or payload.get("type")

    if not name:
        raise ConfigError("Each identity provider must include a name")
    if not idp_type:
        raise ConfigError(f"Identity provider '{name}' must include a type")

    idp_type = str(idp_type).upper()
    payload["name"] = name
    payload["type"] = idp_type

    if idp_type not in SUPPORTED_TYPES:
        raise ConfigError(
            f"Identity provider '{name}' has unsupported type '{idp_type}'. "
            f"Supported types: {', '.join(sorted(SUPPORTED_TYPES))}"
        )

    if idp_type in {"SAML2", "OIDC"}:
        if not isinstance(payload.get("protocol"), dict):
            raise ConfigError(f"Identity provider '{name}' must include protocol object")
        if not isinstance(payload.get("policy"), dict):
            raise ConfigError(f"Identity provider '{name}' must include policy object")

    return payload


def build_plan(idp_configs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for index, idp_config in enumerate(idp_configs):
        payload = build_payload(idp_config)
        name = payload["name"]
        if name in seen_names:
            raise ConfigError(f"Duplicate identity provider name in input: {name}")
        seen_names.add(name)
        plan.append(
            {
                "index": index,
                "name": name,
                "type": payload["type"],
                "description": idp_config.get("description", ""),
                "reason": idp_config.get("reason", ""),
                "action": "create",
                "payload": payload,
            }
        )
    return plan
