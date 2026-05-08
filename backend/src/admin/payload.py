"""Admin mode_payload data management functions.

Provides table validation, column reading, filtering, sorting, and CRUD
operations for mode_payload_* tables across public and created schemas.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from db import connect as db_connect, quote_identifier


def connect(db_path: str | Path) -> Any:
    return db_connect(db_path)


# ---------------------------------------------------------------------------
# mode_payload 表直读 / 直写 (站点数据管理页)
# ---------------------------------------------------------------------------

_MODE_PAYLOAD_TABLE_RE = re.compile(r"^mode_payload_\d+$")


def validate_mode_payload_table(table_name: str) -> str:
    """安全校验：只允许 mode_payload_{数字} 格式的表名，防止 SQL 注入。"""
    table_name = str(table_name or "").strip()
    if not _MODE_PAYLOAD_TABLE_RE.match(table_name):
        raise ValueError(f"无效的 mode_payload 表名: {table_name}")
    return table_name


def normalize_mode_payload_source(source: str) -> str:
    """统一归一后台 mode_payload 数据源参数。"""
    normalized = str(source or "public").strip().lower()
    if normalized not in {"public", "created", "all"}:
        raise ValueError(f"不支持的数据源: {source}")
    return normalized


def mode_payload_table_exists(conn: Any, table_name: str, source: str) -> bool:
    """判断 public / created schema 下的目标表是否存在。"""
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
    """读取目标表列名，兼容 public / created schema。"""
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


def build_admin_mode_payload_filters(
    columns: tuple[str, ...],
    type_filter: str = "",
    web_filter: str = "",
    search: str = "",
) -> tuple[list[str], list[Any]]:
    """构建 mode_payload 列表页筛选条件。"""
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
        search_term = f"%{search.strip()}%"
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
    """按 year / term / 来源 / 创建时间排序。"""

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


def fetch_mode_payload_source_rows(
    conn: Any,
    table_name: str,
    source: str,
    type_filter: str = "",
    web_filter: str = "",
    search: str = "",
) -> tuple[list[dict[str, Any]], list[str]]:
    """读取单一数据源下的 mode_payload 行数据。"""
    normalized_source = normalize_mode_payload_source(source)
    if normalized_source == "all":
        raise ValueError("fetch_mode_payload_source_rows 不支持 all，请分别读取 public / created。")

    if not mode_payload_table_exists(conn, table_name, normalized_source):
        return [], []

    columns = mode_payload_table_columns(conn, table_name, normalized_source)
    if not columns:
        return [], []

    where_clauses, params = build_admin_mode_payload_filters(
        columns,
        type_filter=type_filter,
        web_filter=web_filter,
        search=search,
    )
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    qualified_table = (
        f'{quote_identifier("created")}.{quote_identifier(table_name)}'
        if normalized_source == "created"
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


def normalize_mode_payload_row_id(row_id: Any) -> Any:
    """兼容 public 整数 id 与 created 的 `c123` 字符串 id。"""
    text = str(row_id or "").strip()
    if not text:
        raise ValueError("row_id 不能为空。")
    return int(text) if text.isdigit() else text


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
    """新版 mode_payload 列表：支持 public / created / all 三种数据源。"""
    table_name = validate_mode_payload_table(table_name)
    page = max(1, int(page))
    page_size = min(max(1, int(page_size)), 200)
    normalized_source = normalize_mode_payload_source(source)

    with connect(db_path) as conn:
        if normalized_source == "all":
            public_rows, public_columns = fetch_mode_payload_source_rows(
                conn,
                table_name,
                "public",
                type_filter=type_filter,
                web_filter=web_filter,
                search=search,
            )
            created_rows, created_columns = fetch_mode_payload_source_rows(
                conn,
                table_name,
                "created",
                type_filter=type_filter,
                web_filter=web_filter,
                search=search,
            )
            merged_rows = (
                [row | {"data_source": "public"} for row in public_rows]
                + [row | {"data_source": "created"} for row in created_rows]
            )
            merged_columns: list[str] = ["data_source"]
            for column_name in [*public_columns, *created_columns]:
                if column_name not in merged_columns:
                    merged_columns.append(column_name)
            sorted_rows = sort_mode_payload_rows(merged_rows)
            total = len(sorted_rows)
            offset = (page - 1) * page_size
            return {
                "rows": sorted_rows[offset: offset + page_size],
                "total": total,
                "page": page,
                "page_size": page_size,
                "columns": merged_columns,
            }

        rows, columns = fetch_mode_payload_source_rows(
            conn,
            table_name,
            normalized_source,
            type_filter=type_filter,
            web_filter=web_filter,
            search=search,
        )
        sorted_rows = sort_mode_payload_rows(rows)
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
    """新版更新接口：支持修改 public 或 created schema 中的记录。"""
    table_name = validate_mode_payload_table(table_name)
    normalized_source = normalize_mode_payload_source(source)
    if normalized_source == "all":
        raise ValueError("全部数据视图不支持直接修改，请指定原始数据或生成数据。")

    qualified_table = (
        f'{quote_identifier("created")}.{quote_identifier(table_name)}'
        if normalized_source == "created"
        else quote_identifier(table_name)
    )
    normalized_row_id = normalize_mode_payload_row_id(row_id)

    with connect(db_path) as conn:
        if not mode_payload_table_exists(conn, table_name, normalized_source):
            raise ValueError(f"table not found: {table_name}")

        existing = mode_payload_table_columns(conn, table_name, normalized_source)
        updates: dict[str, Any] = {}
        for key, value in data.items():
            if key in {"id", "table_modes_id", "data_source"}:
                continue
            if key in existing:
                updates[key] = value

        if not updates:
            raise ValueError("no editable columns provided")

        set_clause = ", ".join(f"{quote_identifier(key)} = ?" for key in updates.keys())
        values = list(updates.values()) + [normalized_row_id]
        conn.execute(
            f"UPDATE {qualified_table} SET {set_clause} WHERE id = ?",
            values,
        )
        conn.commit()

        row = conn.execute(
            f"SELECT * FROM {qualified_table} WHERE id = ?",
            (normalized_row_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"row not found: {row_id}")
        return {"row": dict(row)}


def delete_mode_payload_row(
    db_path: str | Path,
    table_name: str,
    row_id: Any,
    source: str = "public",
) -> None:
    """新版删除接口：支持删除 public 或 created schema 中的记录。"""
    table_name = validate_mode_payload_table(table_name)
    normalized_source = normalize_mode_payload_source(source)
    if normalized_source == "all":
        raise ValueError("全部数据视图不支持直接删除，请指定原始数据或生成数据。")

    qualified_table = (
        f'{quote_identifier("created")}.{quote_identifier(table_name)}'
        if normalized_source == "created"
        else quote_identifier(table_name)
    )
    normalized_row_id = normalize_mode_payload_row_id(row_id)

    with connect(db_path) as conn:
        if not mode_payload_table_exists(conn, table_name, normalized_source):
            raise ValueError(f"table not found: {table_name}")

        existing = conn.execute(
            f"SELECT id FROM {qualified_table} WHERE id = ?",
            (normalized_row_id,),
        ).fetchone()
        if not existing:
            raise ValueError(f"row not found: {row_id}")

        conn.execute(
            f"DELETE FROM {qualified_table} WHERE id = ?",
            (normalized_row_id,),
        )
        conn.commit()
