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
