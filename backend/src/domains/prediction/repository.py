"""预测领域数据访问层（Repository）。

站点预测模块、预测生成记录相关的 SQL 查询集中在这里。
"""

from __future__ import annotations

from typing import Any


def list_site_modules(conn: Any, site_id: int) -> list[dict[str, Any]]:
    """查询指定站点的所有预测模块。"""
    rows = conn.execute(
        """
        SELECT id, site_id, mechanism_key, mode_id, status, sort_order, created_at, updated_at
        FROM site_prediction_modules
        WHERE site_id = ?
        ORDER BY sort_order, id
        """,
        (site_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def find_site_module(conn: Any, site_id: int, module_id: int) -> dict[str, Any] | None:
    """查询指定站点的单个预测模块。"""
    row = conn.execute(
        "SELECT * FROM site_prediction_modules WHERE id = ? AND site_id = ?",
        (module_id, site_id),
    ).fetchone()
    return dict(row) if row else None


def count_site_modules(conn: Any, site_id: int) -> int:
    """查询站点预测模块数量。"""
    row = conn.execute(
        "SELECT COUNT(*) AS total FROM site_prediction_modules WHERE site_id = ?",
        (site_id,),
    ).fetchone()
    return int(row["total"] or 0)


def get_enabled_module_keys(conn: Any, site_id: int) -> list[str]:
    """查询站点所有启用的预测模块 mechanism_key 列表。"""
    rows = conn.execute(
        """
        SELECT mechanism_key FROM site_prediction_modules
        WHERE site_id = ? AND status = 1
        ORDER BY sort_order, id
        """,
        (site_id,),
    ).fetchall()
    return [str(row["mechanism_key"]) for row in rows]
