"""Domain service helpers for admin mode_payload access control."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from core.errors import ForbiddenError, NotFoundError
from db import connect
from db import quote_identifier

from .mode_payload_repository import (
    delete_mode_payload_row_by_id,
    fetch_mode_payload_source_rows,
    get_mode_payload_row,
    get_mode_payload_row_web_values,
    mode_payload_table_columns,
    mode_payload_table_exists,
    update_mode_payload_row_values,
)

_MODE_PAYLOAD_TABLE_RE = re.compile(r"^mode_payload_\d+$")


def validate_mode_payload_table(table_name: str) -> str:
    table_name = str(table_name or "").strip()
    if not _MODE_PAYLOAD_TABLE_RE.match(table_name):
        raise ValueError(f"invalid mode_payload table name: {table_name}")
    return table_name


def normalize_mode_payload_source(source: str) -> str:
    normalized = str(source or "public").strip().lower()
    if normalized not in {"public", "created", "all"}:
        raise ValueError(f"unsupported mode_payload source: {source}")
    return normalized


def normalize_mode_payload_row_id(row_id: Any, source: str = "public") -> Any:
    text = str(row_id or "").strip()
    if not text:
        raise ValueError("row_id cannot be empty")
    normalized_source = normalize_mode_payload_source(source)
    if normalized_source == "created":
        return text
    return int(text) if text.isdigit() else text


def build_mode_payload_filters(
    columns: tuple[str, ...],
    type_filter: str = "",
    web_filter: str = "",
    search: str = "",
) -> tuple[list[str], list[Any]]:
    where_clauses: list[str] = []
    params: list[Any] = []

    if str(type_filter).strip():
        if "type" in columns:
            where_clauses.append(f"CAST({quote_identifier('type')} AS TEXT) = ?")
            params.append(str(type_filter).strip())
        else:
            where_clauses.append("1 = 0")

    if str(web_filter).strip():
        web_columns = [column_name for column_name in ("web_id", "web") if column_name in columns]
        if web_columns:
            where_clauses.append(
                "(" + " OR ".join(
                    f"CAST({quote_identifier(column_name)} AS TEXT) = ?"
                    for column_name in web_columns
                ) + ")"
            )
            params.extend([str(web_filter).strip()] * len(web_columns))
        else:
            where_clauses.append("1 = 0")

    if str(search).strip():
        search_term = f"%{str(search).strip()}%"
        search_clauses = [
            f"CAST({quote_identifier(column_name)} AS TEXT) LIKE ?"
            for column_name in columns
            if column_name != "id"
        ]
        if search_clauses:
            where_clauses.append(f"({' OR '.join(search_clauses)})")
            params.extend([search_term] * len(search_clauses))

    return where_clauses, params


def sort_mode_payload_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def parse_int_like(value: Any) -> int:
        text = str(value or "").strip()
        if not text:
            return -1
        normalized = re.sub(r"^[cC]", "", text)
        normalized = re.sub(r"[^\d-]", "", normalized)
        try:
            return int(normalized)
        except ValueError:
            return -1

    def row_key(row: dict[str, Any]) -> tuple[int, int, int, int, str]:
        source_rank = 1 if str(row.get("data_source") or "").strip().lower() == "created" else 0
        return (
            parse_int_like(row.get("year")),
            parse_int_like(row.get("term")),
            source_rank,
            parse_int_like(row.get("source_record_id") or row.get("id")),
            str(row.get("created_at") or ""),
        )

    return sorted(rows, key=row_key, reverse=True)


def _load_mode_payload_source_rows(
    conn: Any,
    table_name: str,
    source: str,
    type_filter: str = "",
    web_filter: str = "",
    search: str = "",
) -> tuple[list[dict[str, Any]], list[str]]:
    normalized_source = normalize_mode_payload_source(source)
    if normalized_source == "all":
        raise ValueError("fetch one source at a time")

    if not mode_payload_table_exists(conn, table_name, normalized_source):
        return [], []

    columns = mode_payload_table_columns(conn, table_name, normalized_source)
    if not columns:
        return [], []

    where_clauses, params = build_mode_payload_filters(
        columns,
        type_filter=type_filter,
        web_filter=web_filter,
        search=search,
    )
    return fetch_mode_payload_source_rows(
        conn,
        table_name,
        normalized_source,
        where_clauses,
        params,
    )


def list_mode_payload_rows(
    db_path: str | Path,
    table_name: str,
    type_filter: str = "",
    web_filter: str = "",
    page: int = 1,
    page_size: int = 50,
    search: str = "",
    source: str = "public",
) -> dict[str, Any]:
    validated_table = validate_mode_payload_table(table_name)
    page = max(1, int(page))
    page_size = min(max(1, int(page_size)), 100)
    normalized_source = normalize_mode_payload_source(source)

    with connect(db_path) as conn:
        if normalized_source == "all":
            public_rows, public_columns = _load_mode_payload_source_rows(
                conn,
                validated_table,
                "public",
                type_filter=type_filter,
                web_filter=web_filter,
                search=search,
            )
            created_rows, created_columns = _load_mode_payload_source_rows(
                conn,
                validated_table,
                "created",
                type_filter=type_filter,
                web_filter=web_filter,
                search=search,
            )
            merged_rows = (
                [row | {"data_source": "public"} for row in public_rows]
                + [row | {"data_source": "created"} for row in created_rows]
            )
            columns: list[str] = ["data_source"]
            for column_name in [*public_columns, *created_columns]:
                if column_name not in columns:
                    columns.append(column_name)
        else:
            merged_rows, columns = _load_mode_payload_source_rows(
                conn,
                validated_table,
                normalized_source,
                type_filter=type_filter,
                web_filter=web_filter,
                search=search,
            )

    sorted_rows = sort_mode_payload_rows(merged_rows)
    total = len(sorted_rows)
    offset = (page - 1) * page_size
    return {
        "rows": sorted_rows[offset: offset + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
        "columns": columns,
    }


def update_mode_payload_row(
    db_path: str | Path,
    table_name: str,
    row_id: Any,
    data: dict[str, Any],
    source: str = "public",
) -> dict[str, Any]:
    validated_table = validate_mode_payload_table(table_name)
    normalized_source = normalize_mode_payload_source(source)
    if normalized_source == "all":
        raise ValueError("all source cannot be updated directly")

    normalized_row_id = normalize_mode_payload_row_id(row_id, normalized_source)
    with connect(db_path) as conn:
        if not mode_payload_table_exists(conn, validated_table, normalized_source):
            raise ValueError(f"table not found: {validated_table}")

        existing_columns = set(mode_payload_table_columns(conn, validated_table, normalized_source))
        updates = {
            key: value
            for key, value in data.items()
            if key not in {"id", "table_modes_id", "data_source"} and key in existing_columns
        }
        if not updates:
            raise ValueError("no editable columns provided")

        update_mode_payload_row_values(
            conn,
            validated_table,
            normalized_row_id,
            source=normalized_source,
            updates=updates,
        )
        conn.commit()

        row = get_mode_payload_row(
            conn,
            validated_table,
            normalized_row_id,
            source=normalized_source,
        )
        if not row:
            raise ValueError(f"row not found: {row_id}")
        return {"row": row}


def delete_mode_payload_row(
    db_path: str | Path,
    table_name: str,
    row_id: Any,
    source: str = "public",
) -> None:
    validated_table = validate_mode_payload_table(table_name)
    normalized_source = normalize_mode_payload_source(source)
    if normalized_source == "all":
        raise ValueError("all source cannot be deleted directly")

    normalized_row_id = normalize_mode_payload_row_id(row_id, normalized_source)
    with connect(db_path) as conn:
        if not mode_payload_table_exists(conn, validated_table, normalized_source):
            raise ValueError(f"table not found: {validated_table}")

        if not get_mode_payload_row(
            conn,
            validated_table,
            normalized_row_id,
            source=normalized_source,
        ):
            raise ValueError(f"row not found: {row_id}")

        delete_mode_payload_row_by_id(
            conn,
            validated_table,
            normalized_row_id,
            source=normalized_source,
        )
        conn.commit()


def ensure_mode_payload_row_belongs_to_site(
    db_path: str | Path,
    table_name: str,
    row_id: Any,
    *,
    source: str = "public",
    site_web_id: int,
) -> None:
    normalized_source = normalize_mode_payload_source(source)
    validated_table = validate_mode_payload_table(table_name)
    normalized_row_id = normalize_mode_payload_row_id(row_id, normalized_source)

    with connect(db_path) as conn:
        if not mode_payload_table_exists(conn, validated_table, normalized_source):
            raise NotFoundError(f"table not found: {validated_table}")

        columns = set(mode_payload_table_columns(conn, validated_table, normalized_source))
        web_columns = [column_name for column_name in ("web_id", "web") if column_name in columns]
        if not web_columns:
            return

        row = get_mode_payload_row_web_values(
            conn,
            validated_table,
            normalized_row_id,
            source=normalized_source,
            web_columns=web_columns,
        )
        if not row:
            raise NotFoundError(f"row not found: {row_id}")

        for column_name in web_columns:
            if str(row[column_name] or "").strip() == str(site_web_id):
                return

        raise ForbiddenError(
            f"site web_id={site_web_id} cannot access another site's mode_payload row"
        )

