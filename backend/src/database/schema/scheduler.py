"""scheduler_tasks 表 —— 带业务上下文字段的调度任务表。"""

from __future__ import annotations

from typing import Any

from database.migrations import add_column_if_missing


def ensure_scheduler_tables(conn: Any, pk_sql: str) -> None:
    """创建调度任务表：scheduler_tasks。"""
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS scheduler_tasks (
            {pk_sql},
            task_key TEXT NOT NULL UNIQUE,
            task_type TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{{}}',
            status TEXT NOT NULL DEFAULT 'pending',
            run_at TEXT NOT NULL,
            locked_at TEXT,
            locked_by TEXT,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL DEFAULT 3,
            last_error TEXT,
            last_finished_at TEXT,
            -- 业务上下文字段（用于后台任务筛选和日志定位）
            site_id INTEGER,
            web_id INTEGER,
            lottery_type_id INTEGER,
            year INTEGER,
            term INTEGER,
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    add_column_if_missing(conn, "scheduler_tasks", "site_id", "INTEGER")
    add_column_if_missing(conn, "scheduler_tasks", "web_id", "INTEGER")
    add_column_if_missing(conn, "scheduler_tasks", "lottery_type_id", "INTEGER")
    add_column_if_missing(conn, "scheduler_tasks", "year", "INTEGER")
    add_column_if_missing(conn, "scheduler_tasks", "term", "INTEGER")
    add_column_if_missing(conn, "scheduler_tasks", "created_by", "TEXT")
