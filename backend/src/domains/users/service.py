"""Admin user service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from auth import hash_password, public_user
from db import connect, utc_now
from helpers import parse_bool
from tables import ensure_admin_tables


def list_users(db_path: str | Path) -> list[dict[str, Any]]:
    """List admin users with sensitive fields removed."""
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM admin_users ORDER BY id").fetchall()
        return [public_user(row) for row in rows]


def save_user(
    db_path: str | Path,
    payload: dict[str, Any],
    user_id: int | None = None,
) -> dict[str, Any]:
    """Create or update an admin user."""
    ensure_admin_tables(db_path)
    now = utc_now()
    username = str(payload.get("username") or "").strip()
    display_name = str(payload.get("display_name") or username).strip()
    role = str(payload.get("role") or "admin").strip()
    status = 1 if parse_bool(payload.get("status"), True) else 0
    password = str(payload.get("password") or "")
    if not username:
        raise ValueError("管理员用户名不能为空")

    with connect(db_path) as conn:
        if user_id is None:
            if not password:
                raise ValueError("新增管理员必须设置密码")
            row = conn.execute(
                """
                INSERT INTO admin_users (
                    username, display_name, password_hash, role, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                (username, display_name, hash_password(password, db_path=db_path), role, status, now, now),
            ).fetchone()
            return public_user(row)

        existing = conn.execute("SELECT * FROM admin_users WHERE id = ?", (user_id,)).fetchone()
        if not existing:
            raise KeyError(f"user_id={user_id} 不存在")
        password_hash = hash_password(password, db_path=db_path) if password else existing["password_hash"]
        row = conn.execute(
            """
            UPDATE admin_users
            SET username = ?,
                display_name = ?,
                password_hash = ?,
                role = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?
            RETURNING *
            """,
            (username, display_name, password_hash, role, status, now, user_id),
        ).fetchone()
        return public_user(row)


def delete_user(db_path: str | Path, user_id: int) -> None:
    """Delete an admin user while preserving at least one active admin."""
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        total = int(
            conn.execute("SELECT COUNT(*) AS total FROM admin_users WHERE status = 1").fetchone()["total"]
            or 0
        )
        target = conn.execute("SELECT status FROM admin_users WHERE id = ?", (user_id,)).fetchone()
        if not target:
            raise KeyError(f"user_id={user_id} 不存在")
        if total <= 1 and int(target["status"] or 0) == 1:
            raise ValueError("至少保留一个可登录管理员")
        conn.execute("DELETE FROM admin_users WHERE id = ?", (user_id,))
