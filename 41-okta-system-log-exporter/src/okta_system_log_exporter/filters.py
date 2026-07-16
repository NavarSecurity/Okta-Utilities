from __future__ import annotations

from typing import Iterable

from .config import ExportConfig


def escape_filter_value(value: str) -> str:
    return value.replace('\\', '\\\\').replace('"', '\\"')


def eq_group(field_name: str, values: Iterable[str]) -> str | None:
    clean_values = [v for v in values if v]
    if not clean_values:
        return None
    expressions = [f'{field_name} eq "{escape_filter_value(value)}"' for value in clean_values]
    if len(expressions) == 1:
        return expressions[0]
    return "(" + " or ".join(expressions) + ")"


def build_generated_filter(cfg: ExportConfig) -> str | None:
    parts = [
        eq_group("eventType", cfg.event_types),
        eq_group("actor.id", cfg.actor_ids),
        eq_group("actor.alternateId", cfg.actor_logins),
        eq_group("target.id", cfg.target_ids),
        eq_group("target.type", cfg.target_types),
        eq_group("outcome.result", cfg.outcomes),
    ]
    clean_parts = [part for part in parts if part]
    if not clean_parts:
        return None
    return " and ".join(clean_parts)


def build_filter(cfg: ExportConfig) -> str | None:
    custom_filter = cfg.filter.strip() if cfg.filter and cfg.filter.strip() else None
    generated = build_generated_filter(cfg)
    if custom_filter and generated:
        return f"({custom_filter}) and ({generated})"
    return custom_filter or generated


def build_query_params(cfg: ExportConfig) -> dict[str, str | int]:
    params: dict[str, str | int] = {
        "since": cfg.resolved_since,
        "limit": cfg.limit,
        "sortOrder": cfg.sort_order,
    }
    if cfg.resolved_until:
        params["until"] = cfg.resolved_until
    filter_value = build_filter(cfg)
    if filter_value:
        params["filter"] = filter_value
    if cfg.q:
        params["q"] = cfg.q
    return params
