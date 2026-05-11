"""Admin authentication and session management."""

from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from db import connect, utc_now
from runtime_config import get_bootstrap_config_value, get_config
from tables import ensure_admin_tables


def _password_iterations(db_path: str | Path | None = None) -> int:
    value = get_bootstrap_config_value("auth.password_iterations", 260000)
    if db_path:
        try:
            value = get_config(db_path, "auth.password_iterations", value)
        except Exception:
            pass
    try:
        return max(100000, int(value))
    except (TypeError, ValueError):
        return 260000


def _session_ttl_seconds(db_path: str | Path) -> int:
    try:
        value = get_config(db_path, "auth.session_ttl_seconds", 86400)
        return max(60, int(value))
    except (TypeError, ValueError):
        return 86400


def hash_password(password: str, salt: str | None = None, db_path: str | Path | None = None) -> str:
    if not password:
        raise ValueError("密码不能为空")
    iterations = _password_iterations(db_path)
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
        created_at = utc_now()
        expires_at = (
            datetime.now(timezone.utc) + timedelta(seconds=_session_ttl_seconds(db_path))
        ).isoformat()
        conn.execute("DELETE FROM admin_sessions WHERE user_id = ?", (row["id"],))
        conn.execute(
            """
            INSERT INTO admin_sessions (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, row["id"], created_at, expires_at),
        )
        conn.execute(
            "UPDATE admin_users SET last_login_at = ?, updated_at = ? WHERE id = ?",
            (created_at, created_at, row["id"]),
        )
        refreshed = conn.execute(
            "SELECT * FROM admin_users WHERE id = ?",
            (row["id"],),
        ).fetchone()
        return {"token": token, "expires_at": expires_at, "user": public_user(refreshed)}


def auth_user_from_token(db_path: str | Path, token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT s.expires_at, u.*
            FROM admin_sessions s
            JOIN admin_users u ON u.id = s.user_id
            WHERE s.token = ? AND u.status = 1
            """,
            (token,),
        ).fetchone()
        if not row:
            return None

        expires_at = str(row.get("expires_at") or "").strip()
        if expires_at:
            try:
                expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            except ValueError:
                conn.execute("DELETE FROM admin_sessions WHERE token = ?", (token,))
                return None
            if expires_dt <= datetime.now(timezone.utc):
                conn.execute("DELETE FROM admin_sessions WHERE token = ?", (token,))
                return None

        return public_user(row)


def ensure_generation_permission(user: dict[str, Any] | None) -> None:
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
