from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from db import connect
from helpers import load_fixed_data_maps
from runtime_config import get_config_from_conn
from utils.created_prediction_store import (
    CREATED_SCHEMA_NAME,
    quote_qualified_identifier,
    schema_table_exists,
    validate_mode_payload_table_name,
)

from .backfill_repository import (
    get_latest_opened_draw_issue,
    list_opened_draws,
    update_created_prediction_result_fields,
)
from .result_fields import compute_res_fields

logger = logging.getLogger("admin.backfill")


def _get_config(conn: Any, key: str, default: Any) -> Any:
    return get_config_from_conn(conn, key, default)


def parse_issue(issue_str: str) -> tuple[int, int]:
    digits = str(issue_str or "").strip()
    if len(digits) < 5:
        raise ValueError(f"期号格式无效: {issue_str}，请输入完整期号（例如 2026001）")
    year = int(digits[:4])
    term = int(digits[4:])
    return year, term


def resolve_backfill_issue_range(
    conn: Any,
    *,
    lottery_type_id: int,
    start_issue: str,
    end_issue: str,
    recent_count: int | None,
) -> tuple[str, str]:
    if start_issue or end_issue:
        return start_issue, end_issue

    effective_recent_count = (
        int(_get_config(conn, "prediction.recent_period_count", 10))
        if recent_count is None
        else int(recent_count)
    )
    if effective_recent_count <= 0:
        raise ValueError("recent_count 必须大于 0")

    current = get_latest_opened_draw_issue(conn, lottery_type_id)
    if not current:
        raise ValueError("没有已开奖记录，无法推算期号范围")

    max_terms = int(_get_config(conn, "prediction.max_terms_per_year", 365))
    end_year, end_term = int(current["year"]), int(current["term"])
    start_year, start_term = end_year, end_term
    for _ in range(effective_recent_count - 1):
        if start_term > 1:
            start_term -= 1
        else:
            start_year -= 1
            start_term = max_terms
    return f"{start_year}{start_term:03d}", f"{end_year}{end_term:03d}"


def list_opened_draws_for_issue_range(
    conn: Any,
    *,
    lottery_type_id: int,
    start_year: int,
    start_term: int,
    end_year: int,
    end_term: int,
) -> list[dict[str, Any]]:
    return [
        draw
        for draw in list_opened_draws(conn, lottery_type_id)
        if (start_year, start_term) <= (int(draw["year"] or 0), int(draw["term"] or 0)) <= (end_year, end_term)
    ]


def backfill_single_draw(
    conn: Any,
    *,
    lottery_type_id: int,
    year: int,
    term: int,
    numbers: str,
    zodiac_map: dict,
    color_map: dict,
    target_tables: list[str] | None = None,
) -> dict[str, Any]:
    res_sx, res_color = compute_res_fields(numbers, zodiac_map, color_map)
    tables = target_tables or conn.list_tables("mode_payload_")
    updated_tables: list[dict[str, Any]] = []
    total_affected = 0

    for table_name in tables:
        if not schema_table_exists(conn, CREATED_SCHEMA_NAME, table_name):
            continue
        qualified = quote_qualified_identifier(CREATED_SCHEMA_NAME, table_name)
        try:
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
            if affected > 0:
                updated_tables.append({"table": table_name, "affected": affected})
                total_affected += affected
        except Exception:
            continue

    return {
        "year": year,
        "term": term,
        "issue": f"{year}{term:03d}",
        "numbers": numbers,
        "res_sx": res_sx,
        "res_color": res_color,
        "updated_tables": updated_tables,
        "total_affected": total_affected,
    }


def normalize_target_tables(raw_table_names: list[Any]) -> list[str] | None:
    if not raw_table_names:
        return None
    if not isinstance(raw_table_names, list):
        raise ValueError("table_names 必须为数组")
    target_tables = list({
        validate_mode_payload_table_name(str(item or "").strip())
        for item in raw_table_names
        if str(item or "").strip()
    })
    if not target_tables:
        raise ValueError("table_names 不能为空")
    return target_tables


def run_backfill_predictions(
    db_path: str | Path,
    *,
    lottery_type_id: int,
    start_issue: str = "",
    end_issue: str = "",
    recent_count: int | None = None,
    target_tables: list[str] | None = None,
) -> dict[str, Any]:
    with connect(db_path) as conn:
        start_issue, end_issue = resolve_backfill_issue_range(
            conn,
            lottery_type_id=lottery_type_id,
            start_issue=start_issue,
            end_issue=end_issue,
            recent_count=recent_count,
        )
        if not start_issue:
            raise ValueError("缺少 start_issue 参数")
        if not end_issue:
            raise ValueError("缺少 end_issue 参数")

        start_year, start_term = parse_issue(start_issue)
        end_year, end_term = parse_issue(end_issue)
        if (start_year, start_term) > (end_year, end_term):
            raise ValueError("起始期号不能大于结束期号")

        target_draws = list_opened_draws_for_issue_range(
            conn,
            lottery_type_id=lottery_type_id,
            start_year=start_year,
            start_term=start_term,
            end_year=end_year,
            end_term=end_term,
        )
        if not target_draws:
            raise ValueError(f"期号范围 {start_issue}-{end_issue} 内没有已开奖记录")

        zodiac_map, color_map = load_fixed_data_maps(conn)
        draw_reports: list[dict[str, Any]] = []
        total_affected = 0
        per_table: dict[str, dict[str, int]] = {}

        for draw in target_draws:
            year = int(draw["year"] or 0)
            term = int(draw["term"] or 0)
            numbers = str(draw["numbers"] or "")

            report = backfill_single_draw(
                conn,
                lottery_type_id=lottery_type_id,
                year=year,
                term=term,
                numbers=numbers,
                zodiac_map=zodiac_map,
                color_map=color_map,
                target_tables=target_tables,
            )
            draw_reports.append(report)
            total_affected += report["total_affected"]

            for table_result in report.get("updated_tables", []):
                table_name = table_result["table"]
                if table_name not in per_table:
                    per_table[table_name] = {"updated": 0, "backfilled": 0}
                per_table[table_name]["updated"] += 1
                per_table[table_name]["backfilled"] += table_result["affected"]

        conn.commit()

    affected_tables = [name for name, stats in per_table.items() if stats["updated"] > 0]
    logger.info(
        "Backfill 完成汇总 — 彩种=%s 范围=%s-%s 已开奖期数=%d 涉及表数=%d 总更新行数=%d",
        lottery_type_id,
        start_issue,
        end_issue,
        len(target_draws),
        len(affected_tables),
        total_affected,
    )
    for table_name in sorted(per_table.keys()):
        stats = per_table[table_name]
        if stats["updated"] > 0:
            logger.info(
                "  -> mode_payload=%s 更新记录=%d 回填字段数=%d",
                table_name,
                stats["updated"],
                stats["backfilled"],
            )

    per_table_summary = [
        {"table": table_name, "updated": stats["updated"], "backfilled": stats["backfilled"]}
        for table_name, stats in sorted(per_table.items())
        if stats["updated"] > 0
    ]
    return {
        "lottery_type_id": lottery_type_id,
        "start_issue": start_issue,
        "end_issue": end_issue,
        "draw_count": len(target_draws),
        "total_affected": total_affected,
        "tables_affected": len(affected_tables),
        "per_table": per_table_summary,
        "draws": draw_reports,
    }
