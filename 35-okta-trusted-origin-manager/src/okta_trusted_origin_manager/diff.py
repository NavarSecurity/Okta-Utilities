from __future__ import annotations

from typing import Any

from .normalize import comparison_view, extract_trusted_origins, key_for_origin, normalize_trusted_origin


def compare_trusted_origins(source_payload: Any, target_payload: Any, match_by: str = "origin", include_status: bool = True) -> dict[str, Any]:
    source = extract_trusted_origins(source_payload)
    target = extract_trusted_origins(target_payload)

    source_map = {key_for_origin(item, match_by): item for item in source if key_for_origin(item, match_by)}
    target_map = {key_for_origin(item, match_by): item for item in target if key_for_origin(item, match_by)}

    missing_in_target = []
    extra_in_target = []
    modified = []
    unchanged = []

    for key, source_item in source_map.items():
        target_item = target_map.get(key)
        if target_item is None:
            missing_in_target.append(normalize_trusted_origin(source_item))
            continue
        source_view = comparison_view(source_item, include_status=include_status)
        target_view = comparison_view(target_item, include_status=include_status)
        if source_view == target_view:
            unchanged.append(normalize_trusted_origin(source_item))
        else:
            changed_fields = []
            for field in sorted(set(source_view) | set(target_view)):
                if source_view.get(field) != target_view.get(field):
                    changed_fields.append(
                        {
                            "field": field,
                            "source": source_view.get(field),
                            "target": target_view.get(field),
                        }
                    )
            modified.append(
                {
                    "key": key,
                    "source": normalize_trusted_origin(source_item),
                    "target": normalize_trusted_origin(target_item),
                    "changedFields": changed_fields,
                }
            )

    for key, target_item in target_map.items():
        if key not in source_map:
            extra_in_target.append(normalize_trusted_origin(target_item))

    return {
        "matchBy": match_by,
        "sourceCount": len(source),
        "targetCount": len(target),
        "missingInTarget": missing_in_target,
        "extraInTarget": extra_in_target,
        "modified": modified,
        "unchanged": unchanged,
        "summary": {
            "sourceOrigins": len(source),
            "targetOrigins": len(target),
            "missingInTarget": len(missing_in_target),
            "extraInTarget": len(extra_in_target),
            "modified": len(modified),
            "unchanged": len(unchanged),
            "totalDifferences": len(missing_in_target) + len(extra_in_target) + len(modified),
        },
    }
