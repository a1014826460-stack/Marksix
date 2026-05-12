"""error_logs 表 —— 结构化错误日志表。"""

from __future__ import annotations

from typing import Any

from database.migrations import add_column_if_missing


def ensure_log_tables(conn: Any, pk_sql: str) -> None:
    """创建错误日志表：error_logs。

    业务上下文字段（site_id、web_id 等）通过 add_column_if_missing
    逐步补齐，兼容旧部署。
    """
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS error_logs (
            {pk_sql},
            created_at TEXT NOT NULL,
            level TEXT NOT NULL DEFAULT 'ERROR',
            logger_name TEXT NOT NULL DEFAULT '',
            module TEXT NOT NULL DEFAULT '',
            func_name TEXT NOT NULL DEFAULT '',
            file_path TEXT NOT NULL DEFAULT '',
            line_number INTEGER NOT NULL DEFAULT 0,
            message TEXT NOT NULL DEFAULT '',
            exc_type TEXT,
            exc_message TEXT,
            stack_trace TEXT,
            user_id TEXT,
            request_params TEXT,
            duration_ms REAL,
            extra_data TEXT
        )
        """
    )
    add_column_if_missing(conn, "error_logs", "site_id", "INTEGER")
    add_column_if_missing(conn, "error_logs", "web_id", "INTEGER")
    add_column_if_missing(conn, "error_logs", "lottery_type_id", "INTEGER")
    add_column_if_missing(conn, "error_logs", "year", "INTEGER")
    add_column_if_missing(conn, "error_logs", "term", "INTEGER")
    add_column_if_missing(conn, "error_logs", "task_key", "TEXT")
    add_column_if_missing(conn, "error_logs", "task_type", "TEXT")
    add_column_if_missing(conn, "error_logs", "request_path", "TEXT")
    add_column_if_missing(conn, "error_logs", "request_method", "TEXT")
