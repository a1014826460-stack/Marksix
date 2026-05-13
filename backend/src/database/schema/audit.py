"""draw_audit_log 表 —— 开奖审计日志。"""

from __future__ import annotations

from typing import Any


def ensure_audit_tables(conn: Any, pk_sql: str) -> None:
    """创建开奖审计日志表：draw_audit_log。"""
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS draw_audit_log (
            {pk_sql},
            lottery_type_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            term INTEGER NOT NULL,
            event TEXT NOT NULL,
            event_time TEXT NOT NULL,
            duration_ms INTEGER,
            status TEXT NOT NULL DEFAULT 'success',
            detail TEXT,
            operator TEXT NOT NULL DEFAULT 'scheduler',
            created_at TEXT NOT NULL
        )
        """
    )
