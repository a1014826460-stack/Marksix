"""Lightweight schema migration helpers."""

from __future__ import annotations

from typing import Any

from database.connection import quote_identifier


def add_column_if_missing(conn: Any, table_name: str, column_name: str, definition: str) -> None:
    """Add a column only when it is missing."""
    columns = set(conn.table_columns(table_name))
    if column_name not in columns:
        conn.execute(
            f"ALTER TABLE {quote_identifier(table_name)} "
            f"ADD COLUMN {quote_identifier(column_name)} {definition}"
        )


def drop_column_if_exists(conn: Any, table_name: str, column_name: str) -> None:
    """Drop a column only when it exists."""
    columns = set(conn.table_columns(table_name))
    if column_name not in columns:
        return
    if getattr(conn, "engine", "") == "postgres":
        conn.execute(
            f"ALTER TABLE {quote_identifier(table_name)} "
            f"DROP COLUMN IF EXISTS {quote_identifier(column_name)}"
        )
        return
    conn.execute(
        f"ALTER TABLE {quote_identifier(table_name)} "
        f"DROP COLUMN {quote_identifier(column_name)}"
    )


ensure_column = add_column_if_missing
