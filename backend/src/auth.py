"""Auth functions extracted from app.py for admin user authentication and session management.

Contains password hashing/verification (PBKDF2-SHA256), user login/logout,
token-based authentication, and admin permission checks.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from pathlib import Path
from typing import Any

from db import connect, utc_now
from tables import ensure_admin_tables


def hash_password(password: str, salt: str | None = None) -> str:
    """使用 PBKDF2 保存管理员密码，避免明文密码进入 SQLite。

    这里不引入第三方认证框架，密码格式固定为
    `pbkdf2_sha256$iterations$salt$hash`，后续迁移到其他框架时也容易转换。
    """
    if not password:
        raise ValueError("密码不能为空")
    iterations = 260_000
    resolved_salt = salt or secrets.token_urlsafe(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        resolved_salt.encode("utf-8"),
        iterations,
    )
    encoded = base64.b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${iterations}${resolved_salt}${encoded}"


def verify_password(password: str, password_hash: str) -> bool:
    """校验管理员密码，兼容当前 PBKDF2 哈希格式。"""
    try:
        algorithm, iterations, salt, expected = password_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    )
    actual = base64.b64encode(digest).decode("ascii")
    return secrets.compare_digest(actual, expected)


def public_user(row: Any) -> dict[str, Any]:
    """过滤密码哈希，只向前端返回可展示的管理员信息。"""
    data = dict(row)
    data.pop("password_hash", None)
    data["status"] = bool(data["status"])
    return data


def login_user(db_path: str | Path, username: str, password: str) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM admin_users WHERE username = ? AND status = 1",
            (username,),
        ).fetchone()
        if not row or not verify_password(password, row["password_hash"]):
            raise PermissionError("用户名或密码错误")

        token = secrets.token_urlsafe(32)
        now = utc_now()
        conn.execute(
            "INSERT INTO admin_sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, row["id"], now),
        )
        conn.execute(
            "UPDATE admin_users SET last_login_at = ?, updated_at = ? WHERE id = ?",
            (now, now, row["id"]),
        )
        refreshed = conn.execute("SELECT * FROM admin_users WHERE id = ?", (row["id"],)).fetchone()
        return {"token": token, "user": public_user(refreshed)}


def auth_user_from_token(db_path: str | Path, token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT u.*
            FROM admin_sessions s
            JOIN admin_users u ON u.id = s.user_id
            WHERE s.token = ? AND u.status = 1
            """,
            (token,),
        ).fetchone()
        return public_user(row) if row else None


def ensure_generation_permission(user: dict[str, Any] | None) -> None:
    """只有后台管理员才能主动触发生成预测。"""
    if not user:
        raise PermissionError("未登录或登录已失效")
    role = str(user.get("role") or "").strip().lower()
    if role not in {"admin", "super_admin"}:
        raise PermissionError("当前账号没有主动生成预测数据的权限")


def logout_user(db_path: str | Path, token: str | None) -> None:
    if not token:
        return
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        conn.execute("DELETE FROM admin_sessions WHERE token = ?", (token,))
