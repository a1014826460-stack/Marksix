from __future__ import annotations

from typing import Any, Iterable

from utils.created_prediction_store import (
    CREATED_SCHEMA_NAME,
    quote_qualified_identifier,
    table_column_names,
)

RESULT_FIELD_COLUMNS = ("res_code", "res_sx", "res_color")


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


def backfill_created_result_fields(
    conn: Any,
    *,
    table_names: Iterable[str],
    lottery_type_id: int,
    year: int,
    term: int,
    numbers: str,
    res_sx: str,
    res_color: str,
    overwrite: bool = False,
) -> dict[str, int]:
    """逐表回填 created 结果字段，单表失败不会拖垮整次回填。

    PostgreSQL 里一条失败语句会让整个事务进入 aborted 状态，之后任何语句（包括
    `information_schema` 探测）都会报 "current transaction is aborted"，于是原先
    "循环内 try/except 后 continue" 的写法会让**其它所有表**已经写入的更新一起丢失：
    线上 `created.mode_payload_273` / `created.mode_payload_335` 没有 `res_*` 列，
    每次开奖后自动回填都会整体失败，已开奖期的结果字段因此长期为空。

    这里对每张表：
    1. 先建 SAVEPOINT；
    2. 探测目标表是否真的具备 `res_*` 列，缺列直接跳过（根因修复）；
    3. 执行回填（`overwrite=False` 逐列只填空值，`True` 允许整行覆盖，仅管理台手动回填使用）；
    4. 任何异常回滚到 SAVEPOINT 后继续下一张表，绝不污染外层事务。

    :return: `{table_name: affected_rows}`，只包含真正更新到行的表。
    """
    filled: dict[str, int] = {}
    for index, raw_name in enumerate(table_names):
        table_name = str(raw_name or "").strip()
        if not table_name:
            continue
        savepoint = f"pred_res_backfill_{index}"
        qualified = quote_qualified_identifier(CREATED_SCHEMA_NAME, table_name)
        conn.execute(f"SAVEPOINT {savepoint}")
        try:
            columns = set(table_column_names(conn, CREATED_SCHEMA_NAME, table_name))
            if not set(RESULT_FIELD_COLUMNS).issubset(columns):
                conn.execute(f"RELEASE SAVEPOINT {savepoint}")
                continue
            if overwrite:
                affected = update_created_prediction_result_fields(
                    conn,
                    qualified_table=qualified,
                    lottery_type_id=lottery_type_id,
                    year=year,
                    term=term,
                    numbers=numbers,
                    res_sx=res_sx,
                    res_color=res_color,
                )
            else:
                affected = fill_missing_created_prediction_result_fields(
                    conn,
                    qualified_table=qualified,
                    lottery_type_id=lottery_type_id,
                    year=year,
                    term=term,
                    numbers=numbers,
                    res_sx=res_sx,
                    res_color=res_color,
                )
        except Exception:
            conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            conn.execute(f"RELEASE SAVEPOINT {savepoint}")
            continue
        conn.execute(f"RELEASE SAVEPOINT {savepoint}")
        if affected > 0:
            filled[table_name] = affected
    return filled
