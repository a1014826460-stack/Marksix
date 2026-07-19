from __future__ import annotations

import os
from collections.abc import Iterable

from core.errors import ValidationError


MAX_JSON_BODY_BYTES = 1024 * 1024
MAX_PUBLIC_HISTORY_LIMIT = 50
MAX_LEGACY_LIST_LIMIT = 100
MAX_ADMIN_LIST_LIMIT = 500


def parse_bounded_int(
    value: object,
    *,
    default: int,
    minimum: int = 1,
    maximum: int,
    field_name: str,
) -> int:
    if value in (None, ""):
        return default
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} 必须为整数") from exc
    if parsed < minimum:
        raise ValidationError(f"{field_name} 必须大于等于 {minimum}")
    return min(parsed, maximum)


def parse_json_content_length(value: object, *, maximum: int = MAX_JSON_BODY_BYTES) -> int:
    try:
        length = int(str(value or "0").strip())
    except (TypeError, ValueError) as exc:
        raise ValidationError("Content-Length 非法") from exc
    if length < 0:
        raise ValidationError("Content-Length 非法")
    if length > maximum:
        raise ValidationError("请求体过大")
    return length


def cors_allowed_origin(request_origin: str | None) -> str | None:
    origin = str(request_origin or "").strip()
    if not origin:
        return None
    configured = _configured_origins()
    return origin if origin in configured else None


def _configured_origins() -> set[str]:
    raw_values: Iterable[str] = (
        os.environ.get("LOTTERY_CORS_ALLOWED_ORIGINS", ""),
        os.environ.get("LOTTERY_PUBLIC_CORS_ALLOWED_ORIGINS", ""),
    )
    return {
        item.strip().rstrip("/")
        for raw in raw_values
        for item in raw.split(",")
        if item.strip()
    }
