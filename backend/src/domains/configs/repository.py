"""配置领域数据访问层（Repository）。

封装 system_config 表的读写操作。
"""

from __future__ import annotations

from typing import Any

from runtime_config import CONFIG_TABLE_NAME


def list_configs(conn: Any, prefix: str = "") -> list[dict[str, Any]]:
    """列出系统配置表中的配置记录。"""
    rows = conn.execute(
        f"""
        SELECT key, value_text, value_type, description, is_secret, updated_at
        FROM {CONFIG_TABLE_NAME}
        WHERE (? = '' OR key LIKE ?)
        ORDER BY key
        """,
        (prefix, f"{prefix}%"),
    ).fetchall()
    return [dict(row) for row in rows]


def find_config_by_key(conn: Any, key: str) -> dict[str, Any] | None:
    """根据 key 查询单个配置。"""
    row = conn.execute(
        f"SELECT key, value_text, value_type, description, is_secret, updated_at FROM {CONFIG_TABLE_NAME} WHERE key = ? LIMIT 1",
        (key,),
    ).fetchone()
    return dict(row) if row else None


def upsert_config(
    conn: Any, key: str, value_text: str, value_type: str,
    description: str, is_secret: int, timestamp: str,
) -> None:
    """插入或更新配置项。"""
    existing = conn.execute(
        f"SELECT id FROM {CONFIG_TABLE_NAME} WHERE key = ? LIMIT 1", (key,)
    ).fetchone()
    if existing:
        conn.execute(
            f"""
            UPDATE {CONFIG_TABLE_NAME}
            SET value_text = ?, value_type = ?, description = ?, is_secret = ?, updated_at = ?
            WHERE key = ?
            """,
            (value_text, value_type, description, is_secret, timestamp, key),
        )
    else:
        conn.execute(
            f"""
            INSERT INTO {CONFIG_TABLE_NAME} (key, value_text, value_type, description, is_secret, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (key, value_text, value_type, description, is_secret, timestamp, timestamp),
        )


def record_config_history(
    conn: Any, config_key: str, old_value: str, new_value: str,
    changed_by: str, changed_at: str, change_reason: str, source: str = "admin",
) -> None:
    """写入配置变更历史。"""
    conn.execute(
        """
        INSERT INTO system_config_history (config_key, old_value, new_value, changed_by, changed_at, change_reason, source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (config_key, old_value, new_value, changed_by, changed_at, change_reason, source),
    )


def query_config_history(
    conn: Any, config_key: str = "", page: int = 1, page_size: int = 30,
) -> tuple[list[dict[str, Any]], int]:
    """分页查询配置变更历史。"""
    filters: list[str] = []
    params: list[Any] = []
    if config_key:
        filters.append("config_key = ?")
        params.append(config_key)
    where = (" WHERE " + " AND ".join(filters)) if filters else ""
    offset = max(0, page - 1) * page_size

    total = int(
        conn.execute(f"SELECT COUNT(*) AS cnt FROM system_config_history{where}", params).fetchone()["cnt"] or 0
    )
    rows = conn.execute(
        f"SELECT * FROM system_config_history{where} ORDER BY changed_at DESC LIMIT ? OFFSET ?",
        params + [page_size, offset],
    ).fetchall()
    return [dict(row) for row in rows], total
