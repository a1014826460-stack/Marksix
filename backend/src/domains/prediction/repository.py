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


def get_enabled_module_rows(conn: Any, site_id: int, mechanism_keys: list[str] | None = None) -> list[dict[str, Any]]:
    """查询站点所有启用状态的预测模块行，可按 mechanism_key 过滤。"""
    query = """
        SELECT id, mechanism_key, mode_id, status, sort_order
        FROM site_prediction_modules
        WHERE site_id = ? AND status = 1
    """
    params: list[Any] = [site_id]
    if mechanism_keys:
        placeholders = ", ".join("?" for _ in mechanism_keys)
        query += f" AND mechanism_key IN ({placeholders})"
        params.extend(mechanism_keys)
    query += " ORDER BY sort_order, id"
    return [dict(row) for row in conn.execute(query, params).fetchall()]


def insert_module(conn: Any, site_id: int, mechanism_key: str, mode_id: int,
                  status: int, sort_order: int, now: str) -> dict[str, Any]:
    """插入一个新的预测模块行，返回新建的行数据。"""
    row = conn.execute(
        """
        INSERT INTO site_prediction_modules (
            site_id, mechanism_key, mode_id, status, sort_order, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        RETURNING *
        """,
        (site_id, mechanism_key, mode_id, status, sort_order, now, now),
    ).fetchone()
    return dict(row)


def update_module(conn: Any, module_id: int, site_id: int, mechanism_key: str,
                  mode_id: int, status: int, sort_order: int, now: str) -> dict[str, Any] | None:
    """更新指定预测模块，返回更新后的行数据。"""
    row = conn.execute(
        """
        UPDATE site_prediction_modules
        SET mechanism_key = ?, mode_id = ?, status = ?, sort_order = ?, updated_at = ?
        WHERE id = ? AND site_id = ?
        RETURNING *
        """,
        (mechanism_key, mode_id, status, sort_order, now, module_id, site_id),
    ).fetchone()
    return dict(row) if row else None


def delete_module(conn: Any, module_id: int, site_id: int) -> bool:
    """删除指定预测模块，返回是否成功删除。"""
    row = conn.execute(
        "DELETE FROM site_prediction_modules WHERE id = ? AND site_id = ? RETURNING id",
        (module_id, site_id),
    ).fetchone()
    return row is not None


def copy_modules_from_template(conn: Any, source_site_id: int, target_site_id: int, now: str) -> int:
    """从模板站点复制预测模块配置到目标站点，返回复制的模块数。"""
    template_modules = conn.execute(
        """
        SELECT mechanism_key, mode_id, status, sort_order
        FROM site_prediction_modules
        WHERE site_id = ?
        ORDER BY sort_order, id
        """,
        (source_site_id,),
    ).fetchall()
    count = 0
    for tm in template_modules:
        conn.execute(
            """
            INSERT INTO site_prediction_modules (
                site_id, mechanism_key, mode_id, status, sort_order, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(site_id, mechanism_key) DO NOTHING
            """,
            (target_site_id, tm["mechanism_key"], tm["mode_id"],
             tm["status"], tm["sort_order"], now, now),
        )
        count += 1
    return count
