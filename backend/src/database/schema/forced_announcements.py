"""Schema helpers for versioned forced announcements."""

from __future__ import annotations

from typing import Any


def ensure_forced_announcement_tables(conn: Any, pk_sql: str) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS forced_announcements (
            {pk_sql},
            version TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            html TEXT NOT NULL,
            scope TEXT NOT NULL CHECK (scope IN ('all_sites', 'selected_sites')),
            starts_at TEXT NOT NULL,
            ends_at TEXT,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS forced_announcement_sites (
            announcement_id INTEGER NOT NULL,
            site_id INTEGER NOT NULL,
            PRIMARY KEY (announcement_id, site_id),
            FOREIGN KEY (announcement_id)
                REFERENCES forced_announcements(id) ON DELETE CASCADE,
            FOREIGN KEY (site_id)
                REFERENCES managed_sites(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_forced_announcements_effective
        ON forced_announcements (enabled, starts_at, ends_at, id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_forced_announcement_sites_site
        ON forced_announcement_sites (site_id, announcement_id)
        """
    )

