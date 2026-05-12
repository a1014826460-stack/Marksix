"""managed_sites / site_fetch_runs 表 —— 托管站点与抓取运行记录。"""

from __future__ import annotations

from typing import Any

from database.migrations import add_column_if_missing


def ensure_site_tables(conn: Any, pk_sql: str) -> None:
    """创建站点相关表：managed_sites、site_fetch_runs。"""
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS managed_sites (
            {pk_sql},
            web_id INTEGER,
            name TEXT NOT NULL,
            domain TEXT,
            lottery_type_id INTEGER,
            enabled INTEGER NOT NULL DEFAULT 1,
            start_web_id INTEGER NOT NULL DEFAULT 1,
            end_web_id INTEGER NOT NULL DEFAULT 10,
            manage_url_template TEXT NOT NULL,
            modes_data_url TEXT NOT NULL,
            token TEXT,
            request_limit INTEGER NOT NULL DEFAULT 250,
            request_delay REAL NOT NULL DEFAULT 0.5,
            announcement TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (lottery_type_id) REFERENCES lottery_types(id) ON DELETE SET NULL
        )
        """
    )
    add_column_if_missing(conn, "managed_sites", "domain", "TEXT")
    add_column_if_missing(conn, "managed_sites", "lottery_type_id", "INTEGER")
    add_column_if_missing(conn, "managed_sites", "announcement", "TEXT")
    add_column_if_missing(conn, "managed_sites", "web_id", "INTEGER")
    # 为已有站点回填 web_id：用 start_web_id 作为默认值
    conn.execute(
        "UPDATE managed_sites SET web_id = start_web_id WHERE web_id IS NULL"
    )

    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS site_fetch_runs (
            {pk_sql},
            site_id INTEGER,
            status TEXT NOT NULL,
            message TEXT,
            modes_count INTEGER NOT NULL DEFAULT 0,
            records_count INTEGER NOT NULL DEFAULT 0,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            FOREIGN KEY (site_id) REFERENCES managed_sites(id) ON DELETE SET NULL
        )
        """
    )
