"""预测模块内部数据库工具函数。

从 predict/mechanisms.py 中提取，供机制算法和配置管理共用。
"""

from __future__ import annotations

from db import ConnectionAdapter
from predict.common import quote_identifier, table_exists

COMMON_PAYLOAD_COLUMNS = {
    "id",
    "web",
    "type",
    "year",
    "term",
    "res_code",
    "res_sx",
    "res_color",
    "status",
    "content",
    "image_url",
    "video_url",
    "web_id",
    "modes_id",
    "source_record_id",
    "fetched_at",
    "month",
    "m_tema",
}


def _table_column_list(conn: ConnectionAdapter, table_name: str) -> tuple[str, ...]:
    return tuple(conn.table_columns(table_name))


def _table_columns(conn: ConnectionAdapter, table_name: str) -> set[str]:
    return set(_table_column_list(conn, table_name))


def _business_columns(conn: ConnectionAdapter, table_name: str) -> tuple[str, ...]:
    """返回去掉公共开奖字段后的业务列，并保持原始列顺序。"""
    return tuple(
        column for column in _table_column_list(conn, table_name)
        if column not in COMMON_PAYLOAD_COLUMNS
    )


def _sample_column_value(conn: ConnectionAdapter, table_name: str, column: str) -> str:
    if column not in _table_columns(conn, table_name):
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


def _sample_content(conn: ConnectionAdapter, table_name: str) -> str:
    if not table_exists(conn, table_name):
        return ""
    columns = _table_columns(conn, table_name)
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


def _is_first_stage_supported_table(columns: set[str]) -> bool:
    """第一阶段只自动处理 content 单字段玩法。"""
    return "content" in columns and not (columns - COMMON_PAYLOAD_COLUMNS)
