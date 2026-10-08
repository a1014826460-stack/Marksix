from __future__ import annotations

from typing import Any

from app_http.request_context import RequestContext
from db import connect
from helpers import apply_public_result_gate


def _has_period_identity(value: Any) -> bool:
    if isinstance(value, list):
        return any(_has_period_identity(item) for item in value)
    if isinstance(value, dict):
        return any(key in value for key in ("year", "term", "issue")) or any(
            _has_period_identity(item) for item in value.values()
        )
    return False


def gate_admin_result_response(ctx: RequestContext, payload: Any, *, default_lottery_type_id: int | None = None) -> Any:
    """Keep admin response outcomes behind full release without changing stored values."""
    ctx.response.set_header("Cache-Control", "no-store")
    if _has_period_identity(payload):
        with connect(ctx.db_path) as conn:
            return apply_public_result_gate(conn, payload, default_lottery_type_id=default_lottery_type_id,
                respect_history_delay=False)
    # Without period identities no database lookup is needed; still apply the fail-closed field policy.
    return apply_public_result_gate(None, payload, default_lottery_type_id=default_lottery_type_id,
        respect_history_delay=False)


def mark_restricted_draw_numbers(payload: Any) -> Any:
    if isinstance(payload, list):
        return [mark_restricted_draw_numbers(item) for item in payload]
    if not isinstance(payload, dict):
        return payload
    result = {key: mark_restricted_draw_numbers(item) for key, item in payload.items()}
    if "numbers" in result:
        result["numbers_restricted"] = result.get("result_restricted") is True
    return result


def gate_admin_draw_management_response(ctx: RequestContext, payload: Any, *, default_lottery_type_id: int | None = None) -> Any:
    """Authenticated Taiwan draw management may inspect all stored numbers.

    This exception restores only numbers on management draw rows, never other
    actual-result aliases or any public/dashboard/prediction response.
    """
    import re

    result = mark_restricted_draw_numbers(gate_admin_result_response(
        ctx, payload, default_lottery_type_id=default_lottery_type_id,
    ))
    user = ctx.state.get("current_user") or {}
    if str(user.get("role") or "").strip().lower() not in {"admin", "super_admin"}:
        return result
    if not re.fullmatch(r"/api/admin/draws(?:/\d+|/auto-fill-future)?", ctx.path):
        return result

    def restore(original: Any, gated: Any) -> Any:
        if isinstance(original, list) and isinstance(gated, list):
            return [restore(before, after) for before, after in zip(original, gated)]
        if not isinstance(original, dict) or not isinstance(gated, dict):
            return gated
        output = {key: restore(original.get(key), value) for key, value in gated.items()}
        try:
            taiwan = int(original.get("lottery_type_id", default_lottery_type_id) or 0) == 3
        except (ValueError, TypeError):
            return output
        if taiwan and "year" in original and "term" in original and "numbers" in original:
            output["numbers"] = original["numbers"]
            output["numbers_restricted"] = False
            # The public gate hides opened state; management must retain the edit lock.
            if "is_opened" in original:
                output["is_opened"] = original["is_opened"]
        return output

    return restore(payload, result)
