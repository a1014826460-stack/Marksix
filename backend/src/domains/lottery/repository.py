"""彩种领域数据访问层（Repository）。

所有彩种和开奖记录相关的 SQL 查询集中在这里。
"""

from __future__ import annotations

from typing import Any


def list_lottery_types(conn: Any) -> list[dict[str, Any]]:
    """查询所有彩种，按启用状态降序、ID 升序排列。"""
    rows = conn.execute(
        "SELECT * FROM lottery_types ORDER BY status DESC, id"
    ).fetchall()
    return [dict(row) for row in rows]


def find_lottery_type_by_id(conn: Any, lottery_type_id: int) -> dict[str, Any] | None:
    """根据 ID 查询彩种。"""
    row = conn.execute(
        "SELECT * FROM lottery_types WHERE id = ?", (lottery_type_id,)
    ).fetchone()
    return dict(row) if row else None


def find_latest_draw(conn: Any, lottery_type_id: int) -> dict[str, Any] | None:
    """查询指定彩种最新一期已开奖记录。"""
    row = conn.execute(
        """
        SELECT year, term, next_term, draw_time, next_time, numbers, is_opened
        FROM lottery_draws
        WHERE lottery_type_id = ?
          AND is_opened = 1
          AND draw_time IS NOT NULL AND draw_time != ''
        ORDER BY year DESC, term DESC, id DESC
        LIMIT 1
        """,
        (lottery_type_id,),
    ).fetchone()
    return dict(row) if row else None


def list_draws(conn: Any, lottery_type_id: int | None = None, limit: int = 200) -> list[dict[str, Any]]:
    """查询开奖记录列表，支持按彩种筛选。"""
    params: list[Any] = []
    where = ""
    if lottery_type_id is not None:
        where = "WHERE d.lottery_type_id = ?"
        params.append(lottery_type_id)
    params.append(limit)
    rows = conn.execute(
        f"""
        SELECT d.*, l.name AS lottery_name
        FROM lottery_draws d
        JOIN lottery_types l ON l.id = d.lottery_type_id
        {where}
        ORDER BY d.year DESC, d.term DESC, d.id DESC
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def find_draw_by_issue(conn: Any, lottery_type_id: int, year: int, term: int) -> dict[str, Any] | None:
    """根据彩种、年份、期号查询开奖记录。"""
    row = conn.execute(
        """
        SELECT * FROM lottery_draws
        WHERE lottery_type_id = ? AND year = ? AND term = ?
        LIMIT 1
        """,
        (lottery_type_id, year, term),
    ).fetchone()
    return dict(row) if row else None


def find_draws_by_year_term_range(
    conn: Any,
    lottery_type_id: int,
    start_year: int,
    start_term: int,
    end_year: int,
    end_term: int,
) -> list[dict[str, Any]]:
    """按年份期号范围查询开奖记录。"""
    rows = conn.execute(
        """
        SELECT * FROM lottery_draws
        WHERE lottery_type_id = ?
          AND (year > ? OR (year = ? AND term >= ?))
          AND (year < ? OR (year = ? AND term <= ?))
        ORDER BY year, term
        """,
        (
            lottery_type_id,
            start_year, start_year, start_term,
            end_year, end_year, end_term,
        ),
    ).fetchall()
    return [dict(row) for row in rows]
