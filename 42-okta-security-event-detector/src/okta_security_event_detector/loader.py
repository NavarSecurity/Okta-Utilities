from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .utils import read_json


def load_events(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Input file not found: {p}")

    if p.suffix.lower() in {".jsonl", ".ndjson"}:
        events: list[dict[str, Any]] = []
        with p.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped:
                    item = json.loads(stripped)
                    if isinstance(item, dict):
                        events.append(item)
        return events

    data = read_json(p)
    if isinstance(data, list):
        return [event for event in data if isinstance(event, dict)]
    if isinstance(data, dict):
        for key in ["events", "systemLogEvents", "data", "items", "results"]:
            value = data.get(key)
            if isinstance(value, list):
                return [event for event in value if isinstance(event, dict)]
        if "uuid" in data or "eventType" in data:
            return [data]
    raise ValueError("Input JSON must be an event array, a JSONL file, or an object containing an events list.")
