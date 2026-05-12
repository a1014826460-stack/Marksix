"""site_prediction_modules / mechanism_status 表 —— 预测模块与机制状态。"""

from __future__ import annotations

from typing import Any

from database.migrations import add_column_if_missing


def ensure_prediction_tables(conn: Any, pk_sql: str) -> None:
    """创建预测相关表：site_prediction_modules、mechanism_status。"""
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS site_prediction_modules (
            {pk_sql},
            site_id INTEGER NOT NULL,
            mechanism_key TEXT NOT NULL,
            mode_id INTEGER,
            status INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(site_id, mechanism_key),
            FOREIGN KEY (site_id) REFERENCES managed_sites(id) ON DELETE CASCADE
        )
        """
    )
    add_column_if_missing(conn, "site_prediction_modules", "mode_id", "INTEGER")

    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS mechanism_status (
            mechanism_key TEXT PRIMARY KEY,
            status INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL
        )
        """
    )
