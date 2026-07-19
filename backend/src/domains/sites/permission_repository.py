"""Persistence operations for per-site administrative permissions."""

from __future__ import annotations

from typing import Any


def has_site_permission(
    conn: Any,
    *,
    user_id: int,
    site_id: int,
    permission: str,
) -> bool:
    column = {
        "view": "can_view",
        "manage": "can_manage",
        "generate": "can_generate",
    }.get(permission)
    if column is None:
        raise ValueError(f"未知站点权限: {permission}")
    row = conn.execute(
        f"SELECT {column} AS allowed FROM site_permissions WHERE user_id = ? AND site_id = ?",
        (user_id, site_id),
    ).fetchone()
    return bool(row and row["allowed"])
