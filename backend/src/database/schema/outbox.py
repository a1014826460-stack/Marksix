"""Schema helper for durable public-publication Outbox events."""

from __future__ import annotations

from typing import Any


PUBLICATION_OUTBOX_TABLE = "publication_outbox"


def ensure_publication_outbox_table(conn: Any, pk_sql: str) -> None:
    """Create the durable Outbox table and its claim lookup indexes.

    The DDL deliberately uses only SQLite/PostgreSQL compatible SQL.  Runtime
    processes do not invoke this helper for PostgreSQL; it is called by the
    explicit migration runner and SQLite's test bootstrap only.
    """
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {PUBLICATION_OUTBOX_TABLE} (
            {pk_sql},
            event_key TEXT NOT NULL UNIQUE,
            event_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            available_at TEXT NOT NULL,
            lease_owner TEXT,
            lease_until TEXT,
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            published_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_publication_outbox_due
        ON {PUBLICATION_OUTBOX_TABLE} (status, available_at, id)
        """
    )
    conn.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_publication_outbox_lease
        ON {PUBLICATION_OUTBOX_TABLE} (status, lease_until, id)
        """
    )
