from __future__ import annotations

from typing import Any


def get_latest_opened_draw_issue(conn: Any, lottery_type_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT year, term
        FROM lottery_draws
        WHERE lottery_type_id = ? AND is_opened = 1
        ORDER BY year DESC, term DESC
        LIMIT 1
        """,
        (lottery_type_id,),
    ).fetchone()
    return dict(row) if row else None


def list_opened_draws(conn: Any, lottery_type_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT year, term, numbers
        FROM lottery_draws
        WHERE lottery_type_id = ?
          AND is_opened = 1
          AND numbers IS NOT NULL AND numbers != ''
        ORDER BY year ASC, term ASC
        """,
        (lottery_type_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def update_created_prediction_result_fields(
    conn: Any,
    *,
    qualified_table: str,
    lottery_type_id: int,
    year: int,
    term: int,
    numbers: str,
    res_sx: str,
    res_color: str,
) -> int:
    cur = conn.execute(
        f"UPDATE {qualified_table} SET res_code = ?, res_sx = ?, res_color = ? "
        "WHERE type = ? AND year = ? AND term = ? "
        "AND ("
        "  res_code IS NULL OR res_code = '' OR REPLACE(res_code, ',', '') = '' "
        "  OR res_sx IS NULL OR res_sx = '' OR REPLACE(res_sx, ',', '') = '' "
        "  OR res_color IS NULL OR res_color = '' OR REPLACE(res_color, ',', '') = '' "
        ")",
        (numbers, res_sx, res_color, str(lottery_type_id), str(year), str(term)),
    )
    return int(cur.rowcount or 0)


def fill_missing_created_prediction_result_fields(
    conn: Any,
    *,
    qualified_table: str,
    lottery_type_id: int,
    year: int,
    term: int,
    numbers: str,
    res_sx: str,
    res_color: str,
) -> int:
    """开奖后自动回填 ``res_code``/``res_sx``/``res_color``，逐列只填空值。

    与 :func:`update_created_prediction_result_fields` 的区别：
    - 那个入口服务于管理台手动回填，允许整行覆盖（管理员手动更改是允许的例外）；
    - 这里是调度器自动回填，只能在字段为空时写入，管理员手工填过的
      ``res_sx``/``res_color`` 不会被自动流程覆盖。

    只更新 ``type + year + term`` 命中的行，且至少一个结果字段为空；预测正文列永不触碰。
    """
    empty_guard = "({column} IS NULL OR {column} = '' OR REPLACE({column}, ',', '') = '')"
    res_code_guard = empty_guard.format(column="res_code")
    res_sx_guard = empty_guard.format(column="res_sx")
    res_color_guard = empty_guard.format(column="res_color")
    cur = conn.execute(
        f"UPDATE {qualified_table} SET "
        f"res_code = CASE WHEN {res_code_guard} THEN ? ELSE res_code END, "
        f"res_sx = CASE WHEN {res_sx_guard} THEN ? ELSE res_sx END, "
        f"res_color = CASE WHEN {res_color_guard} THEN ? ELSE res_color END "
        "WHERE type = ? AND year = ? AND term = ? "
        f"AND ({res_code_guard} OR {res_sx_guard} OR {res_color_guard})",
        (numbers, res_sx, res_color, str(lottery_type_id), str(year), str(term)),
    )
    return int(cur.rowcount or 0)
