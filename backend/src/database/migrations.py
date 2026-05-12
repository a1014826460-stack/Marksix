"""轻量数据库迁移工具。

提供不依赖独立迁移框架的列添加能力，
在 bootstrap 阶段自动补齐缺失列。
"""

from __future__ import annotations

from typing import Any

from database.connection import quote_identifier


def add_column_if_missing(conn: Any, table_name: str, column_name: str, definition: str) -> None:
    """PostgreSQL-compatible lightweight migration helper.

    仅在列不存在时才添加，幂等安全。
    是 ``ensure_admin_tables`` 所用的主要 schema 演进工具。
    """
    columns = set(conn.table_columns(table_name))
    if column_name not in columns:
        conn.execute(
            f"ALTER TABLE {quote_identifier(table_name)} "
            f"ADD COLUMN {quote_identifier(column_name)} {definition}"
        )


# 兼容别名
ensure_column = add_column_if_missing
