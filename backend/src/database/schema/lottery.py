"""lottery_types / lottery_draws 表 —— 彩种与开奖记录。"""

from __future__ import annotations

from typing import Any

from database.migrations import add_column_if_missing


def ensure_lottery_tables(conn: Any, pk_sql: str) -> None:
    """创建彩种相关表：lottery_types、lottery_draws。"""
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS lottery_types (
            {pk_sql},
            name TEXT NOT NULL UNIQUE,
            draw_time TEXT,
            collect_url TEXT,
            status INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    add_column_if_missing(conn, "lottery_types", "next_time", "TEXT")
    add_column_if_missing(conn, "lottery_types", "last_auto_task_status", "TEXT")

    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS lottery_draws (
            {pk_sql},
            lottery_type_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            term INTEGER NOT NULL,
            numbers TEXT NOT NULL,
            draw_time TEXT,
            status INTEGER NOT NULL DEFAULT 1,
            is_opened INTEGER NOT NULL DEFAULT 0,
            next_term INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(lottery_type_id, year, term),
            FOREIGN KEY (lottery_type_id) REFERENCES lottery_types(id) ON DELETE CASCADE
        )
        """
    )
    add_column_if_missing(conn, "lottery_draws", "next_time", "TEXT")
