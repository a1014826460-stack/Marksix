"""system_config_history 表 —— 配置变更历史表。"""

from __future__ import annotations

from typing import Any


def ensure_config_history_tables(conn: Any, pk_sql: str) -> None:
    """创建配置变更历史表：system_config_history。"""
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS system_config_history (
            {pk_sql},
            config_key TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            changed_by TEXT,
            changed_at TEXT NOT NULL,
            change_reason TEXT,
            source TEXT NOT NULL DEFAULT 'admin'
        )
        """
    )
