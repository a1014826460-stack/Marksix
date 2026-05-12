"""legacy_image_assets 表 —— 旧版图片资产表。"""

from __future__ import annotations

from typing import Any

from database.migrations import add_column_if_missing


def ensure_legacy_asset_tables(conn: Any, pk_sql: str) -> None:
    """创建旧版兼容表：legacy_image_assets。"""
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS legacy_image_assets (
            {pk_sql},
            source_key TEXT NOT NULL DEFAULT 'legacy-post-list',
            source_pc INTEGER,
            source_web INTEGER,
            source_type INTEGER,
            title TEXT,
            file_name TEXT NOT NULL UNIQUE,
            storage_path TEXT NOT NULL,
            legacy_upload_path TEXT NOT NULL UNIQUE,
            cover_image TEXT NOT NULL UNIQUE,
            mime_type TEXT NOT NULL,
            file_size INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0,
            enabled INTEGER NOT NULL DEFAULT 1,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    add_column_if_missing(
        conn, "legacy_image_assets", "source_key",
        "TEXT NOT NULL DEFAULT 'legacy-post-list'",
    )
    add_column_if_missing(conn, "legacy_image_assets", "source_pc", "INTEGER")
    add_column_if_missing(conn, "legacy_image_assets", "source_web", "INTEGER")
    add_column_if_missing(conn, "legacy_image_assets", "source_type", "INTEGER")
    add_column_if_missing(conn, "legacy_image_assets", "title", "TEXT")
    add_column_if_missing(conn, "legacy_image_assets", "storage_path", "TEXT")
    add_column_if_missing(conn, "legacy_image_assets", "legacy_upload_path", "TEXT")
    add_column_if_missing(conn, "legacy_image_assets", "cover_image", "TEXT")
    add_column_if_missing(conn, "legacy_image_assets", "mime_type", "TEXT")
    add_column_if_missing(
        conn, "legacy_image_assets", "file_size", "INTEGER NOT NULL DEFAULT 0",
    )
    add_column_if_missing(
        conn, "legacy_image_assets", "sort_order", "INTEGER NOT NULL DEFAULT 0",
    )
    add_column_if_missing(
        conn, "legacy_image_assets", "enabled", "INTEGER NOT NULL DEFAULT 1",
    )
    add_column_if_missing(conn, "legacy_image_assets", "notes", "TEXT")
