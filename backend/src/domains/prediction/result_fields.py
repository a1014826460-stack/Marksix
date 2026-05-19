from __future__ import annotations

from typing import Any

from utils.created_prediction_store import normalize_color_label


def compute_res_fields(
    numbers_str: str,
    zodiac_map: dict[str, Any],
    color_map: dict[str, Any],
) -> tuple[str, str]:
    """Compute res_sx and res_color from one comma-separated draw result string."""
    res_sx_parts: list[str] = []
    res_color_parts: list[str] = []
    for raw_number in (numbers_str or "").split(","):
        text = raw_number.strip()
        if not text:
            continue
        try:
            code = f"{int(text):02d}"
        except ValueError:
            continue
        res_sx_parts.append(str(zodiac_map.get(code) or ""))
        res_color_parts.append(normalize_color_label(color_map.get(code, "")))
    return (
        ",".join(res_sx_parts) if any(res_sx_parts) else "",
        ",".join(res_color_parts) if any(res_color_parts) else "",
    )
