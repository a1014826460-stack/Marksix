"""admin_users / admin_sessions tables for admin auth."""

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
    # Existing databases stored bearer values in token. New sessions use the
    # token_hash lookup column; the legacy token column receives a hash marker.
    columns = set(conn.table_columns("admin_sessions"))
    if "token_hash" not in columns:
        from database.migrations import add_column_if_missing

        add_column_if_missing(conn, "admin_sessions", "token_hash", "TEXT")
        conn.execute(
            "UPDATE admin_sessions SET token_hash = token WHERE token_hash IS NULL OR token_hash = ''"
        )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_admin_sessions_token_hash ON admin_sessions (token_hash)"
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS admin_login_captcha (
            {pk_sql},
            fingerprint TEXT NOT NULL,
            code TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_admin_login_captcha_fingerprint
        ON admin_login_captcha (fingerprint, expires_at)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_login_attempts (
            fingerprint TEXT PRIMARY KEY,
            attempt_count INTEGER NOT NULL DEFAULT 1,
            first_attempt_at TEXT NOT NULL,
            last_attempt_at TEXT NOT NULL,
            locked_until TEXT
        )
        """
    )
