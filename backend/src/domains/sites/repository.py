"""站点领域数据访问层（Repository）。

所有站点相关的 SQL 查询集中在这里。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from db import connect, quote_identifier


def list_all_sites(conn: Any) -> list[dict[str, Any]]:
    """查询所有托管站点，关联彩种名称，按启用状态降序、ID 升序排列。"""
    rows = conn.execute(
        """
        SELECT s.*, l.name AS lottery_name
        FROM managed_sites s
        LEFT JOIN lottery_types l ON l.id = s.lottery_type_id
        ORDER BY s.enabled DESC, s.id ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def find_site_by_id(conn: Any, site_id: int) -> dict[str, Any] | None:
    """根据站点 ID 查询单个站点（含彩种名称）。"""
    row = conn.execute(
        """
        SELECT s.*, l.name AS lottery_name
        FROM managed_sites s
        LEFT JOIN lottery_types l ON l.id = s.lottery_type_id
        WHERE s.id = ?
        """,
        (site_id,),
    ).fetchone()
    return dict(row) if row else None


def find_site_by_domain(conn: Any, domain: str) -> dict[str, Any] | None:
    """根据域名查询站点。"""
    row = conn.execute(
        """
        SELECT s.*, l.name AS lottery_name
        FROM managed_sites s
        LEFT JOIN lottery_types l ON l.id = s.lottery_type_id
        WHERE LOWER(COALESCE(s.domain, '')) = ?
        ORDER BY s.id
        LIMIT 1
        """,
        (domain.strip().lower(),),
    ).fetchone()
    return dict(row) if row else None


def find_first_site(conn: Any) -> dict[str, Any] | None:
    """查询第一个站点（按 ID 排序）。"""
    row = conn.execute(
        """
        SELECT s.*, l.name AS lottery_name
        FROM managed_sites s
        LEFT JOIN lottery_types l ON l.id = s.lottery_type_id
        ORDER BY s.id
        LIMIT 1
        """
    ).fetchone()
    return dict(row) if row else None


def count_sites(conn: Any) -> int:
    """查询站点总数。"""
    row = conn.execute("SELECT COUNT(*) AS total FROM managed_sites").fetchone()
    return int(row["total"] or 0)


def insert_site(conn: Any, fields: dict[str, Any], now: str) -> dict[str, Any]:
    """创建新站点，返回创建后的行。"""
    row = conn.execute(
        """
        INSERT INTO managed_sites (
            web_id, name, domain, lottery_type_id, enabled, start_web_id, end_web_id,
            manage_url_template, modes_data_url, token, request_limit,
            request_delay, announcement, notes,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING *
        """,
        (
            fields["web_id"],
            fields["name"],
            fields["domain"],
            fields["lottery_type_id"],
            fields["enabled"],
            fields["start_web_id"],
            fields["end_web_id"],
            fields["manage_url_template"],
            fields["modes_data_url"],
            fields["token"],
            fields["request_limit"],
            fields["request_delay"],
            fields["announcement"],
            fields["notes"],
            now,
            now,
        ),
    ).fetchone()
    return dict(row)


def update_site(conn: Any, site_id: int, fields: dict[str, Any], now: str) -> dict[str, Any] | None:
    """更新已有站点，返回更新后的行。"""
    row = conn.execute(
        """
        UPDATE managed_sites
        SET name = ?, domain = ?, lottery_type_id = ?, enabled = ?,
            start_web_id = ?, end_web_id = ?,
            manage_url_template = ?, modes_data_url = ?, token = ?,
            request_limit = ?, request_delay = ?,
            announcement = ?, notes = ?,
            updated_at = ?
        WHERE id = ?
        RETURNING *
        """,
        (
            fields["name"],
            fields["domain"],
            fields["lottery_type_id"],
            fields["enabled"],
            fields["start_web_id"],
            fields["end_web_id"],
            fields["manage_url_template"],
            fields["modes_data_url"],
            fields["token"],
            fields["request_limit"],
            fields["request_delay"],
            fields["announcement"],
            fields["notes"],
            now,
            site_id,
        ),
    ).fetchone()
    return dict(row) if row else None


def delete_site_by_id(conn: Any, site_id: int) -> bool:
    """删除指定站点，返回是否成功删除。"""
    cur = conn.execute("DELETE FROM managed_sites WHERE id = ?", (site_id,))
    return cur.rowcount > 0


def get_site_web_id(conn: Any, site_id: int) -> int | None:
    """查询站点的 web_id。"""
    row = conn.execute(
        "SELECT web_id FROM managed_sites WHERE id = ?", (site_id,)
    ).fetchone()
    return int(row["web_id"]) if row and row["web_id"] is not None else None


def backfill_site_web_ids(conn: Any) -> None:
    """为缺少 web_id 的已有站点回填（使用 start_web_id 作为默认值）。"""
    conn.execute(
        "UPDATE managed_sites SET web_id = start_web_id WHERE web_id IS NULL"
    )
