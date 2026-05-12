"""日志领域数据访问层（Repository）。

封装 error_logs 表的查询操作。
"""

from __future__ import annotations

from typing import Any


def query_logs(
    conn: Any,
    *,
    level: str = "",
    module: str = "",
    keyword: str = "",
    site_id: int | None = None,
    web_id: int | None = None,
    lottery_type_id: int | None = None,
    page: int = 1,
    page_size: int = 30,
) -> tuple[list[dict[str, Any]], int]:
    """分页查询错误日志，支持多维度筛选。"""
    filters: list[str] = []
    params: list[Any] = []

    if level:
        filters.append("level = ?")
        params.append(level.upper())
    if module:
        filters.append("module = ?")
        params.append(module)
    if keyword:
        filters.append("(message LIKE ? OR exc_message LIKE ?)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    if site_id is not None:
        filters.append("site_id = ?")
        params.append(site_id)
    if web_id is not None:
        filters.append("web_id = ?")
        params.append(web_id)
    if lottery_type_id is not None:
        filters.append("lottery_type_id = ?")
        params.append(lottery_type_id)

    where = (" WHERE " + " AND ".join(filters)) if filters else ""
    offset = max(0, page - 1) * page_size

    total = int(
        conn.execute(f"SELECT COUNT(*) AS cnt FROM error_logs{where}", params).fetchone()["cnt"] or 0
    )
    rows = conn.execute(
        f"SELECT * FROM error_logs{where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [page_size, offset],
    ).fetchall()
    return [dict(row) for row in rows], total


def get_log_stats(conn: Any) -> dict[str, Any]:
    """获取日志统计信息（各级别数量、模块分布）。"""
    level_counts = conn.execute(
        "SELECT level, COUNT(*) AS cnt FROM error_logs GROUP BY level ORDER BY cnt DESC"
    ).fetchall()
    module_counts = conn.execute(
        "SELECT module, COUNT(*) AS cnt FROM error_logs GROUP BY module ORDER BY cnt DESC LIMIT 10"
    ).fetchall()
    total = int(
        conn.execute("SELECT COUNT(*) AS cnt FROM error_logs").fetchone()["cnt"] or 0
    )
    return {
        "total": total,
        "by_level": {str(row["level"]): int(row["cnt"]) for row in level_counts},
        "by_module": {str(row["module"]): int(row["cnt"]) for row in module_counts},
    }


def get_distinct_modules(conn: Any) -> list[str]:
    """获取所有出现过的日志模块名。"""
    rows = conn.execute(
        "SELECT DISTINCT module FROM error_logs WHERE module != '' ORDER BY module"
    ).fetchall()
    return [str(row["module"]) for row in rows]


def get_distinct_levels(conn: Any) -> list[str]:
    """获取所有出现过的日志级别。"""
    rows = conn.execute(
        "SELECT DISTINCT level FROM error_logs ORDER BY level"
    ).fetchall()
    return [str(row["level"]) for row in rows]


def find_log_by_id(conn: Any, log_id: int) -> dict[str, Any] | None:
    """根据 ID 查询单条日志详情。"""
    row = conn.execute(
        "SELECT * FROM error_logs WHERE id = ?", (log_id,)
    ).fetchone()
    return dict(row) if row else None


def delete_old_logs(conn: Any, before_timestamp: str, level: str | None = None) -> int:
    """清理指定时间之前的日志。"""
    filters = ["created_at < ?"]
    params: list[Any] = [before_timestamp]
    if level:
        filters.append("level = ?")
        params.append(level.upper())
    where = " AND ".join(filters)
    cur = conn.execute(f"DELETE FROM error_logs WHERE {where}", params)
    return cur.rowcount
