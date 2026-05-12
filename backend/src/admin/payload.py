"""
Admin mode_payload 数据管理模块。

提供 mode_payload_* 表的表名校验、列读取、数据查询、筛选排序、
以及 CRUD 操作，同时支持 public 和 created 两种 schema 的数据源。

Provides table validation, column reading, filtering, sorting, and CRUD
operations for mode_payload_* tables across public and created schemas.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from db import connect, quote_identifier


# ---------------------------------------------------------------------------
# mode_payload 表直读 / 直写 (站点数据管理页)
# ---------------------------------------------------------------------------

# 只允许 mode_payload_{数字} 格式的表名，用于防止 SQL 注入
_MODE_PAYLOAD_TABLE_RE = re.compile(r"^mode_payload_\d+$")


def validate_mode_payload_table(table_name: str) -> str:
    """安全校验表名，只允许 ``mode_payload_{数字}`` 格式，防止 SQL 注入。

    :param table_name: 表名（字符串）
    :return: 去除首尾空格后的合法表名
    :raises ValueError: 当表名不符合 ``mode_payload_{数字}`` 格式时抛出
    """
    table_name = str(table_name or "").strip()
    if not _MODE_PAYLOAD_TABLE_RE.match(table_name):
        raise ValueError(f"无效的 mode_payload 表名: {table_name}")
    return table_name


def normalize_mode_payload_source(source: str) -> str:
    """统一归一化后台 mode_payload 数据源参数。

    将数据源参数标准化为以下三者之一：``"public"``、``"created"``、``"all"``。

    :param source: 数据源参数（大小写不敏感，如 "PUBLIC"、"Created" 等）
    :return: 归一化后的数据源字符串（小写）
    :raises ValueError: 当 source 不是 "public"、"created" 或 "all" 时抛出
    """
    normalized = str(source or "public").strip().lower()
    if normalized not in {"public", "created", "all"}:
        raise ValueError(f"不支持的数据源: {source}")
    return normalized


def mode_payload_table_exists(conn: Any, table_name: str, source: str) -> bool:
    """判断 public 或 created schema 下的目标表是否存在。

    :param conn: 数据库连接对象
    :param table_name: 表名
    :param source: 数据源 ("public" 或 "created")
    :return: 表存在则返回 True，否则返回 False
    """
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
    """读取目标表的列名列表，兼容 public 和 created schema。

    :param conn: 数据库连接对象
    :param table_name: 表名
    :param source: 数据源 ("public" 或 "created")
    :return: 列名字符串元组，按序号排列
    """
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
    """构建 mode_payload 列表页的 SQL WHERE 筛选条件。

    支持三种筛选维度：
    - ``type_filter``: 按 type 列精确匹配
    - ``web_filter``: 按 web_id 或 web 列精确匹配（任一列存在即可匹配）
    - ``search``: 按所有列（除 id 外）模糊搜索

    若指定的筛选列在目标表中不存在，则生成 ``1 = 0`` 空条件。

    :param columns: 目标表的列名元组
    :param type_filter: 彩种类型筛选值（字符串），为空则不过滤
    :param web_filter: 站点 web 标识筛选值（字符串），为空则不过滤
    :param search: 模糊搜索关键字，为空则不过滤
    :return: (where_clauses, params) 元组
             - where_clauses: SQL WHERE 子句列表（不含 WHERE 关键字）
             - params: 对应的参数列表
    """
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
    """按 year / term / 数据来源 / 创建时间对 mode_payload 行进行排序。

    排序规则（降序）：
    1. 年份（year）
    2. 期数（term）
    3. 数据来源排名（created > public），确保同一期次下生成数据优先展示
    4. 记录 ID（数字优先，文本取数字部分）
    5. 创建时间（created_at）

    :param rows: 待排序的行字典列表，每行需包含 year、term 等字段
    :return: 排序后的行字典列表
    """

    def parse_int_like(value: Any) -> int:
        """将类似数字的值解析为整数，用于排序比较。不可解析时返回 -1。"""
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
    """从单一数据源（public 或 created）读取 mode_payload 表中的行数据。

    :param conn: 数据库连接对象
    :param table_name: 表名
    :param source: 数据源 ("public" 或 "created"，不支持 "all")
    :param type_filter: 彩种类型筛选值，可选
    :param web_filter: 站点 web 筛选值，可选
    :param search: 模糊搜索关键字，可选
    :return: (rows, columns) 元组
             - rows: 行字典列表
             - columns: 列名列表
    :raises ValueError: 当 source 为 "all" 时抛出（不适用于本函数）
    """
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


def normalize_mode_payload_row_id(row_id: Any, source: str = "public") -> Any:
    """兼容 public 的整数 id 与 created 的字符串 id。

    - ``public``: 纯数字字符串仍归一化为 int，保持与原始表整数主键兼容
    - ``created``: 始终保留为 str，避免 PostgreSQL 在 text 主键上出现 ``text = smallint``

    :param row_id: 行 ID（整数或字符串）
    :param source: 数据源（``public`` / ``created``）
    :return: 归一化后的 ID（int 或 str）
    :raises ValueError: 当 row_id 为空时抛出
    """
    text = str(row_id or "").strip()
    if not text:
        raise ValueError("row_id 不能为空。")
    normalized_source = normalize_mode_payload_source(source)
    if normalized_source == "created":
        return text
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
    """获取 mode_payload 表的行数据列表，支持分页和三种数据源模式。

    数据源模式：
    - ``"public"``: 仅查询 public schema 下的表
    - ``"created"``: 仅查询 created schema 下的表
    - ``"all"``: 合并 public 和 created 两个数据源的结果，
      每行增加 ``data_source`` 字段标记来源

    :param db_path: 数据库文件路径
    :param table_name: mode_payload 表名（必须符合 ``mode_payload_{数字}`` 格式）
    :param type_filter: 彩种类型筛选值，可选
    :param web_filter: 站点 web 筛选值，可选
    :param page: 页码（从 1 开始），默认 1
    :param page_size: 每页条数（1-100），默认 50
    :param search: 模糊搜索关键字，可选
    :param source: 数据源 ("public" / "created" / "all")，默认 "public"
    :return: 字典，包含 rows（当前页行数据列表）、total（总行数）、
             page（当前页码）、page_size（每页条数）、columns（列名列表）
    :raises ValueError: 当表名无效时抛出
    """
    table_name = validate_mode_payload_table(table_name)
    page = max(1, int(page))
    page_size = min(max(1, int(page_size)), 100)
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
    """更新 mode_payload 表中的单行数据。

    支持修改 public 或 created schema 中的记录。
    自动过滤 id、table_modes_id、data_source 等不可编辑的字段，
    仅更新目标表中实际存在的列。

    :param db_path: 数据库文件路径
    :param table_name: mode_payload 表名（必须符合 ``mode_payload_{数字}`` 格式）
    :param row_id: 行 ID（整数或字符串，支持 created 的 "c123" 格式）
    :param data: 要更新的字段字典
    :param source: 数据源 ("public" 或 "created")，不支持 "all"
    :return: 字典，包含 ``row`` 键，值为更新后的行数据字典
    :raises ValueError: 当表名无效、数据源为 "all"、表不存在、
                       无可编辑列、或行 ID 不存在时抛出
    """
    table_name = validate_mode_payload_table(table_name)
    normalized_source = normalize_mode_payload_source(source)
    if normalized_source == "all":
        raise ValueError("全部数据视图不支持直接修改，请指定原始数据或生成数据。")

    qualified_table = (
        f'{quote_identifier("created")}.{quote_identifier(table_name)}'
        if normalized_source == "created"
        else quote_identifier(table_name)
    )
    normalized_row_id = normalize_mode_payload_row_id(row_id, normalized_source)

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
    """从 mode_payload 表中删除单行数据。

    支持删除 public 或 created schema 中的记录。

    :param db_path: 数据库文件路径
    :param table_name: mode_payload 表名（必须符合 ``mode_payload_{数字}`` 格式）
    :param row_id: 行 ID（整数或字符串，支持 created 的 "c123" 格式）
    :param source: 数据源 ("public" 或 "created")，不支持 "all"
    :raises ValueError: 当表名无效、数据源为 "all"、表不存在、或行 ID 不存在时抛出
    """
    table_name = validate_mode_payload_table(table_name)
    normalized_source = normalize_mode_payload_source(source)
    if normalized_source == "all":
        raise ValueError("全部数据视图不支持直接删除，请指定原始数据或生成数据。")

    qualified_table = (
        f'{quote_identifier("created")}.{quote_identifier(table_name)}'
        if normalized_source == "created"
        else quote_identifier(table_name)
    )
    normalized_row_id = normalize_mode_payload_row_id(row_id, normalized_source)

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
