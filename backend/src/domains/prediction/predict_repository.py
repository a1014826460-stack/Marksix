from __future__ import annotations

from typing import Any

from db import quote_identifier


def get_mode_payload_table_title(conn: Any, table_name: str) -> tuple[int | None, str | None]:
    row = conn.execute(
        """
        SELECT modes_id, title
        FROM mode_payload_tables
        WHERE table_name = ?
        """,
        (table_name,),
    ).fetchone()
    if not row:
        return None, None
    return int(row["modes_id"]), str(row["title"])


def load_recent_result_rows(conn: Any, table_name: str, *, limit: int = 10) -> list[Any]:
    return conn.execute(
        f"""
        SELECT * FROM (
            SELECT *
            FROM {quote_identifier(table_name)}
            WHERE res_code IS NOT NULL AND res_code != ''
            ORDER BY CAST(year AS INTEGER) DESC, CAST(term AS INTEGER) DESC
            LIMIT ?
        ) AS recent
        ORDER BY CAST(year AS INTEGER), CAST(term AS INTEGER)
        """,
        (int(limit),),
    ).fetchall()


def table_columns(conn: Any, table_name: str) -> tuple[str, ...]:
    return tuple(conn.table_columns(table_name))


def sample_column_value(conn: Any, table_name: str, column: str) -> str:
    columns = set(table_columns(conn, table_name))
    if column not in columns:
        return ""
    row = conn.execute(
        f"""
        SELECT {quote_identifier(column)}
        FROM {quote_identifier(table_name)}
        WHERE {quote_identifier(column)} IS NOT NULL
          AND {quote_identifier(column)} != ''
        LIMIT 1
        """
    ).fetchone()
    return str(row[column] or "") if row else ""


def sample_content(conn: Any, table_name: str) -> str:
    columns = set(table_columns(conn, table_name))
    if "content" not in columns:
        return ""
    row = conn.execute(
        f"""
        SELECT content
        FROM {quote_identifier(table_name)}
        WHERE content IS NOT NULL AND content != ''
        LIMIT 1
        """
    ).fetchone()
    return str(row["content"] or "") if row else ""


def load_fixed_data_rows(conn: Any, mapping_key: str) -> list[Any]:
    return conn.execute(
        """
        SELECT id, name, code
        FROM fixed_data
        WHERE sign = ?
        ORDER BY CAST(id AS INTEGER)
        """,
        (mapping_key,),
    ).fetchall()


def load_fixed_data_sign_names(conn: Any) -> list[Any]:
    return conn.execute(
        """
        SELECT sign, name FROM fixed_data
        WHERE name IS NOT NULL AND name != ''
        ORDER BY sign, CAST(id AS INTEGER)
        """
    ).fetchall()


def load_non_empty_column_values(conn: Any, table_name: str, column_name: str) -> list[str]:
    rows = conn.execute(
        f"""
        SELECT {quote_identifier(column_name)}
        FROM {quote_identifier(table_name)}
        WHERE {quote_identifier(column_name)} IS NOT NULL
          AND {quote_identifier(column_name)} != ''
        """
    ).fetchall()
    return [str(row[column_name] or "") for row in rows]


def load_limited_non_empty_column_values(
    conn: Any,
    table_name: str,
    column_name: str,
    *,
    limit: int,
) -> list[str]:
    rows = conn.execute(
        f"""
        SELECT {quote_identifier(column_name)}
        FROM {quote_identifier(table_name)}
        WHERE {quote_identifier(column_name)} IS NOT NULL
          AND {quote_identifier(column_name)} != ''
        LIMIT ?
        """,
        (int(limit),),
    ).fetchall()
    return [str(row[column_name] or "") for row in rows]


def load_distinct_non_empty_column_values_by_frequency(
    conn: Any, table_name: str, column_name: str
) -> list[str]:
    rows = conn.execute(
        f"""
        SELECT {quote_identifier(column_name)}
        FROM {quote_identifier(table_name)}
        WHERE {quote_identifier(column_name)} IS NOT NULL
          AND {quote_identifier(column_name)} != ''
        GROUP BY {quote_identifier(column_name)}
        ORDER BY COUNT(*) DESC, {quote_identifier(column_name)}
        """
    ).fetchall()
    return [str(row[column_name] or "") for row in rows]


def load_qinqi_history_rows(conn: Any) -> list[Any]:
    return conn.execute(
        """
        SELECT title, content
        FROM mode_payload_26
        WHERE title IS NOT NULL AND title != ''
          AND content IS NOT NULL AND content != ''
        """
    ).fetchall()


def has_text_history_column_value(
    conn: Any,
    table_name: str,
    column_name: str,
    *,
    mode_column: str = "",
    modes_id: int | None = None,
) -> bool:
    where_parts = [f"COALESCE({quote_identifier(column_name)}, '') != ''"]
    params: list[Any] = []
    if mode_column and modes_id is not None and modes_id >= 0:
        where_parts.insert(0, f"{quote_identifier(mode_column)} = ?")
        params.append(modes_id)
    row = conn.execute(
        f"""
        SELECT 1
        FROM {quote_identifier(table_name)}
        WHERE {" AND ".join(where_parts)}
        LIMIT 1
        """,
        params,
    ).fetchone()
    return bool(row)


def load_random_text_history_row(
    conn: Any,
    table_name: str,
    *,
    mode_column: str = "",
    modes_id: int | None = None,
    non_empty_columns: tuple[str, ...],
) -> Any | None:
    where_parts: list[str] = []
    params: list[Any] = []
    if mode_column and modes_id is not None and modes_id >= 0:
        where_parts.append(f"{quote_identifier(mode_column)} = ?")
        params.append(modes_id)
    text_where = " OR ".join(
        f"COALESCE({quote_identifier(column)}, '') != ''" for column in non_empty_columns
    )
    if text_where:
        where_parts.append(f"({text_where})")
    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    return conn.execute(
        f"""
        SELECT *
        FROM {quote_identifier(table_name)}
        {where_clause}
        ORDER BY RANDOM()
        LIMIT 1
        """,
        params,
    ).fetchone()


def load_latest_columns_by_issue(
    conn: Any,
    table_name: str,
    *,
    columns: tuple[str, ...],
) -> Any | None:
    table_column_set = set(table_columns(conn, table_name))
    selected_sql = ", ".join(quote_identifier(column) for column in columns)
    order_parts: list[str] = []
    if "year" in table_column_set:
        order_parts.append("CAST(year AS INTEGER) DESC")
    if "term" in table_column_set:
        order_parts.append("CAST(term AS INTEGER) DESC")
    if "source_record_id" in table_column_set:
        order_parts.append(
            "CAST(COALESCE(NULLIF(CAST(source_record_id AS TEXT), ''), '0') AS INTEGER) DESC"
        )
    elif "id" in table_column_set:
        order_parts.append(
            "CAST(COALESCE(NULLIF(CAST(id AS TEXT), ''), '0') AS INTEGER) DESC"
        )
    order_clause = f"ORDER BY {', '.join(order_parts)}" if order_parts else ""
    return conn.execute(
        f"""
        SELECT {selected_sql}
        FROM {quote_identifier(table_name)}
        {order_clause}
        LIMIT 1
        """
    ).fetchone()


def load_random_distinct_text_pool_row(
    conn: Any,
    table_name: str,
    *,
    text_column: str,
    selected_columns: tuple[str, ...],
) -> dict[str, str] | None:
    distinct_columns = ", ".join(quote_identifier(column) for column in selected_columns)
    row = conn.execute(
        f"""
        SELECT {distinct_columns}
        FROM (
            SELECT DISTINCT {distinct_columns}
            FROM {quote_identifier(table_name)}
            WHERE {quote_identifier(text_column)} IS NOT NULL
              AND {quote_identifier(text_column)} != ''
        ) AS text_pool
        ORDER BY RANDOM()
        LIMIT 1
        """
    ).fetchone()
    return {key: str(row[key] or "") for key in row.keys()} if row else None


def load_rows_with_non_empty_label_column(
    conn: Any,
    table_name: str,
    *,
    label_column: str,
    selected_columns: tuple[str, ...],
) -> list[Any]:
    selected_sql = ", ".join(quote_identifier(column) for column in selected_columns)
    return conn.execute(
        f"""
        SELECT {selected_sql}
        FROM {quote_identifier(table_name)}
        WHERE {quote_identifier(label_column)} IS NOT NULL
          AND {quote_identifier(label_column)} != ''
        """
    ).fetchall()


def load_mode_payload_table_rows(conn: Any) -> list[Any]:
    return conn.execute(
        """
        SELECT modes_id, title, table_name, record_count
        FROM mode_payload_tables
        ORDER BY modes_id
        """
    ).fetchall()
