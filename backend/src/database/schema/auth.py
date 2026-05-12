"""admin_users / admin_sessions 表 —— 后台认证。"""

from __future__ import annotations

from typing import Any


def ensure_auth_tables(conn: Any, pk_sql: str) -> None:
    """创建认证相关表：admin_users、admin_sessions。"""
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS admin_users (
            {pk_sql},
            username TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin',
            status INTEGER NOT NULL DEFAULT 1,
            last_login_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            FOREIGN KEY (user_id) REFERENCES admin_users(id) ON DELETE CASCADE
        )
        """
    )
