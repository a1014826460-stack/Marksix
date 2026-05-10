from __future__ import annotations

import json
from typing import Any

DEFAULT_DIVERSITY_POLICY = "unique_first_two"
WINDOW_SHARED_DIVERSITY_POLICY = "window_shared"
FREE_DIVERSITY_POLICY = "free"

CONTENT_DIVERSITY_EXEMPT_MODE_IDS = {197}


def resolve_diversity_policy(mode_id: int, config: Any | None = None) -> str:
    policy = str(getattr(config, "diversity_policy", "") or "").strip()
    if policy:
        return policy
    if int(mode_id or 0) in CONTENT_DIVERSITY_EXEMPT_MODE_IDS:
        return WINDOW_SHARED_DIVERSITY_POLICY
    return DEFAULT_DIVERSITY_POLICY


def parse_array_content(content_value: Any) -> list[str] | None:
    if isinstance(content_value, list):
        return [str(item) for item in content_value]
    text = str(content_value or "").strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return None


def dump_array_content(items: list[str], original_value: Any) -> Any:
    if isinstance(original_value, list):
        return items
    return json.dumps(items, ensure_ascii=False)


def content_prefix_signature(content_value: Any, width: int = 2) -> tuple[str, ...] | None:
    items = parse_array_content(content_value)
    if not items:
        return None
    limited = items[: max(1, width)]
    return tuple(str(item) for item in limited)


def enforce_prediction_diversity(
    *,
    mode_id: int,
    row_data: dict[str, Any],
    recent_rows: list[dict[str, Any]] | None = None,
    config: Any | None = None,
) -> dict[str, Any]:
    """Apply the default diversity contract for array-like content.

    Returns the (possibly repaired) row_data dict.  A ``_diversity_warning``
    key is added when diversity could not be resolved after all retries.
    """
    policy = resolve_diversity_policy(mode_id, config)
    if policy in {WINDOW_SHARED_DIVERSITY_POLICY, FREE_DIVERSITY_POLICY}:
        return dict(row_data)

    content_value = row_data.get("content")
    items = parse_array_content(content_value)
    if not items or len(items) < 2:
        return dict(row_data)

    recent = recent_rows or []

    # Build sets of first-item and first-pair signatures from recent rows.
    recent_first: set[str] = set()
    recent_pairs: set[tuple[str, str]] = set()
    for row in recent:
        row_items = parse_array_content(row.get("content"))
        if not row_items:
            continue
        recent_first.add(row_items[0])
        if len(row_items) >= 2:
            recent_pairs.add((row_items[0], row_items[1]))

    current_first = items[0]
    current_pair = (items[0], items[1])

    needs_repair = (current_first in recent_first) or (current_pair in recent_pairs)
    if not needs_repair:
        return dict(row_data)

    best = list(items)
    resolved = False
    for attempt in range(5):
        if attempt == 0:
            best[0], best[1] = best[1], best[0]
        else:
            if len(best) >= 4:
                best[:4] = best[1:4] + [best[0]]
            else:
                best[0], best[1] = best[1], best[0]

        if best[0] not in recent_first and (best[0], best[1]) not in recent_pairs:
            resolved = True
            break

    result = dict(row_data)
    result["content"] = dump_array_content(best, content_value)

    if not resolved:
        result["_diversity_warning"] = (
            f"mode_id={mode_id}: 多样性修复在5次尝试后仍未解决，"
            f"首项={best[0]!r}，保留最后候选值"
        )

    return result
