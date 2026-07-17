"""Traffic event tables for public-site analytics."""

from __future__ import annotations

from typing import Any


def ensure_traffic_tables(conn: Any, pk_sql: str) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS public_site_traffic_events (
            {pk_sql},
            site_key TEXT NOT NULL,
            site_id INTEGER,
            web_id INTEGER,
            lottery_type INTEGER,
            event_type TEXT NOT NULL,
            path TEXT NOT NULL DEFAULT '',
            route TEXT NOT NULL DEFAULT '',
            article_id TEXT NOT NULL DEFAULT '',
            referrer TEXT NOT NULL DEFAULT '',
            utm_source TEXT NOT NULL DEFAULT '',
            utm_medium TEXT NOT NULL DEFAULT '',
            utm_campaign TEXT NOT NULL DEFAULT '',
            user_agent TEXT NOT NULL DEFAULT '',
            ip_hash TEXT NOT NULL DEFAULT '',
            visitor_id TEXT NOT NULL DEFAULT '',
            occurred_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
