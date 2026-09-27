#!/usr/bin/env python
"""补齐 ``created.mode_payload_*`` 里「已开奖但结果字段为空」的历史行。

背景
----
调度器在每次开奖后会调用自动回填，只填空值、绝不触碰预测正文。但历史上有一批行
（例如 ``created.mode_payload_54`` 的 251 行）因为当时的回填实现会整批失败而一直
没有结果字段，前端就只能显示 ``??`` 占位，判定也无法给出。

这个脚本是一次性的**补齐**入口：先按表找出 ``res_code`` 为空且该期已经在
``lottery_draws`` 开奖的 ``(type, year, term)``，再对命中的表逐个回填
``res_code`` / ``res_sx`` / ``res_color``。

安全约束
--------
* 默认 ``--dry-run``：只统计，不写库。
* 只更新 ``type + year + term`` 命中的行，且**逐列只填空值**（``overwrite=False``）；
  管理员手工填过的结果字段不会被覆盖，预测正文列（content/title/image_url…）永远不被触碰。
* 只处理 ``lottery_draws.is_opened = 1`` 的期号，未开奖期一定不动。

用法
----
    cd backend/src
    python ../scripts/backfill_created_result_catchup.py --db-path "$env:DATABASE_URL"
    python ../scripts/backfill_created_result_catchup.py --db-path "$env:DATABASE_URL" --apply
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from db import connect  # noqa: E402
from domains.prediction.backfill_repository import (  # noqa: E402
    RESULT_FIELD_COLUMNS,
    backfill_created_result_fields,
)
from domains.prediction.result_fields import compute_res_fields  # noqa: E402
from helpers import load_fixed_data_maps  # noqa: E402
from utils.created_prediction_store import (  # noqa: E402
    CREATED_SCHEMA_NAME,
    quote_qualified_identifier,
    table_column_names,
)


def collect_gaps(conn: Any) -> dict[tuple[str, int, int], list[str]]:
    """返回 ``{(type, year, term): [表名, …]}``，只包含已开奖且结果为空的期。"""
    gaps: dict[tuple[str, int, int], list[str]] = {}
    for table in sorted(conn.list_tables("mode_payload_")):
        columns = set(table_column_names(conn, CREATED_SCHEMA_NAME, table))
        if not set(RESULT_FIELD_COLUMNS).issubset(columns):
            continue
        qualified = quote_qualified_identifier(CREATED_SCHEMA_NAME, table)
        rows = conn.execute(
            f"SELECT type, year, term FROM {qualified} "
            "WHERE res_code IS NULL OR res_code = '' OR REPLACE(res_code, ',', '') = '' "
            "GROUP BY type, year, term",
        ).fetchall()
        for row in rows:
            key = (str(row["type"] or ""), int(row["year"] or 0), int(row["term"] or 0))
            if not key[0] or not key[1] or not key[2]:
                continue
            gaps.setdefault(key, []).append(table)
    return gaps


def opened_draw_numbers(conn: Any, lottery_type_id: str, year: int, term: int) -> str:
    row = conn.execute(
        "SELECT numbers FROM lottery_draws "
        "WHERE lottery_type_id = ? AND year = ? AND term = ? "
        "  AND is_opened = 1 AND numbers IS NOT NULL AND numbers != ''",
        (str(lottery_type_id), year, term),
    ).fetchone()
    return str(row["numbers"]) if row else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db-path", default=os.environ.get("DATABASE_URL", ""), help="数据库 DSN，默认取 DATABASE_URL")
    parser.add_argument("--apply", action="store_true", help="真正写库；不加则只统计（dry-run）")
    parser.add_argument("--limit", type=int, default=0, help="最多处理多少个期号，0 表示不限制")
    args = parser.parse_args()

    if not args.db_path:
        print("缺少 --db-path（或设置 DATABASE_URL）", file=sys.stderr)
        return 2

    conn = connect(args.db_path)
    gaps = collect_gaps(conn)
    total_rows = len(gaps)
    total_tables = sum(len(tables) for tables in gaps.values())
    print(f"发现缺口期号 {total_rows} 个，涉及 created 表命中 {total_tables} 次")

    if not args.apply:
        for key, tables in sorted(gaps.items())[:20]:
            print(f"  {key[0]}/{key[1]}/{key[2]:03d} → {len(tables)} 张表，例如 {tables[:3]}")
        print("dry-run，未写库。加 --apply 执行补齐。")
        return 0

    zodiac_map, color_map = load_fixed_data_maps(conn)
    items = sorted(gaps.items())
    if args.limit > 0:
        items = items[: args.limit]

    updated_draws = 0
    updated_rows = 0
    skipped = 0
    for (lottery_type_id, year, term), tables in items:
        numbers = opened_draw_numbers(conn, lottery_type_id, year, term)
        if not numbers:
            skipped += 1
            continue
        res_sx, res_color = compute_res_fields(numbers, zodiac_map, color_map)
        filled = backfill_created_result_fields(
            conn,
            table_names=tables,
            lottery_type_id=int(lottery_type_id),
            year=year,
            term=term,
            numbers=numbers,
            res_sx=res_sx,
            res_color=res_color,
            overwrite=False,
        )
        affected = sum(filled.values())
        if affected:
            updated_draws += 1
            updated_rows += affected
            print(f"  {lottery_type_id}/{year}/{term:03d} 回填 {affected} 行（{len(filled)} 张表）")
    conn.commit()
    print(f"完成：{updated_draws} 个期号、共 {updated_rows} 行结果字段被补齐；跳过 {skipped} 个没有开奖号码的期号")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
