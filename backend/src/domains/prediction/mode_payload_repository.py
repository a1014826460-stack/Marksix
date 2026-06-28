"""Repository helpers for admin mode_payload row access checks."""

from __future__ import annotations

from typing import Any

from db import quote_identifier


def mode_payload_table_exists(conn: Any, table_name: str, source: str) -> bool:
    if source == "created":
        row = conn.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'created' AND table_name = ?
            """,
            (table_name,),
        ).fetchone()
        return bool(row)
    return bool(conn.table_exists(table_name))


def mode_payload_table_columns(conn: Any, table_name: str, source: str) -> tuple[str, ...]:
    if source == "created":
        rows = conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'created' AND table_name = ?
            ORDER BY ordinal_position
            """,
            (table_name,),
        ).fetchall()
        return tuple(str(row["column_name"]) for row in rows)
    return tuple(conn.table_columns(table_name))


def get_mode_payload_row_web_values(
    conn: Any,
    table_name: str,
    row_id: Any,
    *,
    source: str,
    web_columns: list[str],
) -> dict[str, Any] | None:
    qualified_table = (
        f'{quote_identifier("created")}.{quote_identifier(table_name)}'
        if source == "created"
        else quote_identifier(table_name)
    )
    select_sql = ", ".join(quote_identifier(column_name) for column_name in web_columns)
    row = conn.execute(
        f"SELECT {select_sql} FROM {qualified_table} WHERE id = ?",
        (row_id,),
    ).fetchone()
    return dict(row) if row else None


def fetch_mode_payload_source_rows(
    conn: Any,
    table_name: str,
    source: str,
    where_clauses: list[str],
    params: list[Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    if not mode_payload_table_exists(conn, table_name, source):
        return [], []

    columns = mode_payload_table_columns(conn, table_name, source)
    if not columns:
        return [], []

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    qualified_table = (
        f'{quote_identifier("created")}.{quote_identifier(table_name)}'
        if source == "created"
        else quote_identifier(table_name)
    )
    rows = conn.execute(
        f"""
        SELECT {", ".join(quote_identifier(column_name) for column_name in columns)}
        FROM {qualified_table}
        {where_sql}
        """,
        params,
    ).fetchall()
    return [dict(row) for row in rows], list(columns)


def update_mode_payload_row_values(
    conn: Any,
    table_name: str,
    row_id: Any,
    *,
    source: str,
    updates: dict[str, Any],
) -> None:
    qualified_table = (
        f'{quote_identifier("created")}.{quote_identifier(table_name)}'
        if source == "created"
        else quote_identifier(table_name)
    )
    set_clause = ", ".join(f"{quote_identifier(key)} = ?" for key in updates)
    values = list(updates.values()) + [row_id]
    conn.execute(
        f"UPDATE {qualified_table} SET {set_clause} WHERE id = ?",
        values,
    )


def get_mode_payload_row(
    conn: Any,
    table_name: str,
    row_id: Any,
    *,
    source: str,
) -> dict[str, Any] | None:
    qualified_table = (
        f'{quote_identifier("created")}.{quote_identifier(table_name)}'
        if source == "created"
        else quote_identifier(table_name)
    )
    row = conn.execute(
        f"SELECT * FROM {qualified_table} WHERE id = ?",
        (row_id,),
    ).fetchone()
    return dict(row) if row else None


def delete_mode_payload_row_by_id(
    conn: Any,
    table_name: str,
    row_id: Any,
    *,
    source: str,
) -> None:
    qualified_table = (
        f'{quote_identifier("created")}.{quote_identifier(table_name)}'
        if source == "created"
        else quote_identifier(table_name)
    )
    conn.execute(
        f"DELETE FROM {qualified_table} WHERE id = ?",
        (row_id,),
    )
