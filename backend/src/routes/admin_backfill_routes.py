from __future__ import annotations

import logging
from typing import Any

from db import connect
from helpers import load_fixed_data_maps
from domains.prediction.regeneration_service import compute_res_fields
from runtime_config import get_config_from_conn
from utils.created_prediction_store import (
    CREATED_SCHEMA_NAME,
    quote_qualified_identifier,
    schema_table_exists,
    validate_mode_payload_table_name,
)

from app_http.request_context import RequestContext
from app_http.router import Router
from app_http.auth import require_authenticated

_backfill_logger = logging.getLogger("admin.backfill")


def register(router: Router) -> None:
    router.add("POST", "/api/admin/backfill-predictions", backfill_predictions,
               guard=require_authenticated)
    router.add("GET", "/api/admin/backfill-predictions/logs", get_backfill_logs,
               guard=require_authenticated)


def _parse_issue(issue_str: str) -> tuple[int, int]:
    """将期号字符串（如 "2026001"）解析为 (year, term) 元组。"""
    digits = str(issue_str or "").strip()
    if len(digits) < 5:
        raise ValueError(f"期号格式无效: {issue_str}，请输入完整期号（例如 2026001）")
    year = int(digits[:4])
    term = int(digits[4:])
    return year, term


def _backfill_single_draw(
    conn: Any,
    lottery_type_id: int,
    year: int,
    term: int,
    numbers_str: str,
    zodiac_map: dict,
    color_map: dict,
    target_tables: list[str] | None = None,
) -> dict[str, Any]:
    """回填单期开奖结果的 res_code / res_sx / res_color 到所有 created 预测表。

    :return: 包含 updated_tables 列表和 total_affected 的字典
    """
    res_sx, res_color = compute_res_fields(numbers_str, zodiac_map, color_map)
    tables = target_tables or conn.list_tables("mode_payload_")
    updated_tables: list[dict[str, Any]] = []
    total_affected = 0

    for table_name in tables:
        if not schema_table_exists(conn, CREATED_SCHEMA_NAME, table_name):
            continue
        qualified = quote_qualified_identifier(CREATED_SCHEMA_NAME, table_name)
        try:
            cur = conn.execute(
                f"UPDATE {qualified} SET res_code = ?, res_sx = ?, res_color = ? "
                "WHERE type = ? AND year = ? AND term = ? "
                "AND ("
                "  res_code IS NULL OR res_code = '' OR REPLACE(res_code, ',', '') = '' "
                "  OR res_sx IS NULL OR res_sx = '' OR REPLACE(res_sx, ',', '') = '' "
                "  OR res_color IS NULL OR res_color = '' OR REPLACE(res_color, ',', '') = '' "
                ")",
                (numbers_str, res_sx, res_color,
                 str(lottery_type_id), str(year), str(term)),
            )
            affected = cur.rowcount
            if affected > 0:
                updated_tables.append({
                    "table": table_name,
                    "affected": affected,
                })
                total_affected += affected
        except Exception:
            continue

    return {
        "year": year,
        "term": term,
        "issue": f"{year}{term:03d}",
        "numbers": numbers_str,
        "res_sx": res_sx,
        "res_color": res_color,
        "updated_tables": updated_tables,
        "total_affected": total_affected,
    }


def backfill_predictions(ctx: RequestContext) -> None:
    """回填预测资料的 res_code / res_sx / res_color。

    请求体（二选一）：
    方式1 — 指定期号范围: {"lottery_type_id": 3, "start_issue": "2026001", "end_issue": "2026010"}
    方式2 — 自动追溯N期: {"lottery_type_id": 3, "recent_count": 10}
    不传 recent_count 时默认使用 prediction.recent_period_count 配置值。
    """
    body = ctx.read_json()
    lottery_type_id = int(body.get("lottery_type_id") or 3)
    start_issue = str(body.get("start_issue") or "")
    end_issue = str(body.get("end_issue") or "")
    recent_count = body.get("recent_count")
    raw_table_names = body.get("table_names") or []

    target_tables: list[str] | None = None
    if raw_table_names:
        if not isinstance(raw_table_names, list):
            ctx.send_json({"ok": False, "error": "table_names 必须为数组"}, 400)
            return
        try:
            target_tables = list({
                validate_mode_payload_table_name(str(item or "").strip())
                for item in raw_table_names
                if str(item or "").strip()
            })
        except ValueError as error:
            ctx.send_json({"ok": False, "error": str(error)}, 400)
            return
        if not target_tables:
            ctx.send_json({"ok": False, "error": "table_names 不能为空"}, 400)
            return

    # 自动推算期号范围：若未指定 start_issue/end_issue，按 recent_count 追溯
    if not start_issue and not end_issue:
        with connect(ctx.db_path) as conn:
            if recent_count is None:
                recent_count = int(get_config_from_conn(conn, "prediction.recent_period_count", 10))
            else:
                recent_count = int(recent_count)
            if recent_count <= 0:
                ctx.send_json({"ok": False, "error": "recent_count 必须大于 0"}, 400)
                return

            current = conn.execute(
                """SELECT year, term FROM lottery_draws
                   WHERE lottery_type_id = ? AND is_opened = 1
                   ORDER BY year DESC, term DESC LIMIT 1""",
                (lottery_type_id,),
            ).fetchone()
            if not current:
                ctx.send_json({"ok": False, "error": "没有已开奖记录，无法推算期号范围"}, 400)
                return

            max_terms = int(get_config_from_conn(conn, "prediction.max_terms_per_year", 365))
            end_year, end_term = int(current["year"]), int(current["term"])
            start_year, start_term = end_year, end_term
            for _ in range(recent_count - 1):
                if start_term > 1:
                    start_term -= 1
                else:
                    start_year -= 1
                    start_term = max_terms
            start_issue = f"{start_year}{start_term:03d}"
            end_issue = f"{end_year}{end_term:03d}"

    if not start_issue:
        ctx.send_json({"ok": False, "error": "缺少 start_issue 参数"}, 400)
        return
    if not end_issue:
        ctx.send_json({"ok": False, "error": "缺少 end_issue 参数"}, 400)
        return

    try:
        start_year, start_term = _parse_issue(start_issue)
        end_year, end_term = _parse_issue(end_issue)
    except ValueError as e:
        ctx.send_json({"ok": False, "error": str(e)}, 400)
        return

    if (start_year, start_term) > (end_year, end_term):
        ctx.send_json({"ok": False, "error": "起始期号不能大于结束期号"}, 400)
        return

    with connect(ctx.db_path) as conn:
        draws = conn.execute(
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

        target_draws = [
            d for d in draws
            if (start_year, start_term) <= (int(d["year"] or 0), int(d["term"] or 0)) <= (end_year, end_term)
        ]

        if not target_draws:
            ctx.send_json({
                "ok": False,
                "error": f"期号范围 {start_issue}-{end_issue} 内没有已开奖记录",
            }, 400)
            return

        zodiac_map, color_map = load_fixed_data_maps(conn)

        draw_reports: list[dict[str, Any]] = []
        total_affected = 0
        per_table: dict[str, dict[str, int]] = {}  # table → {updated, backfilled}

        for draw in target_draws:
            year = int(draw["year"] or 0)
            term = int(draw["term"] or 0)
            numbers_str = str(draw["numbers"] or "")

            report = _backfill_single_draw(
                conn, lottery_type_id, year, term,
                numbers_str, zodiac_map, color_map, target_tables,
            )
            draw_reports.append(report)
            total_affected += report["total_affected"]

            for tb in report.get("updated_tables", []):
                tname = tb["table"]
                if tname not in per_table:
                    per_table[tname] = {"updated": 0, "backfilled": 0}
                per_table[tname]["updated"] += 1
                per_table[tname]["backfilled"] += tb["affected"]

        conn.commit()

        # 按 mode 汇总日志
        affected_tables = [k for k, v in per_table.items() if v["updated"] > 0]
        _backfill_logger.info(
            "Backfill 完成汇总 — 彩种=%s 范围=%s-%s 已开奖期数=%d 涉及表数=%d 总更新行数=%d",
            lottery_type_id, start_issue, end_issue,
            len(target_draws), len(affected_tables), total_affected,
        )
        for tname in sorted(per_table.keys()):
            s = per_table[tname]
            if s["updated"] > 0:
                _backfill_logger.info(
                    "  → mode_payload=%s 更新记录=%d 回填字段数=%d",
                    tname, s["updated"], s["backfilled"],
                )

        per_table_summary = [
            {"table": t, "updated": s["updated"], "backfilled": s["backfilled"]}
            for t, s in sorted(per_table.items()) if s["updated"] > 0
        ]

        ctx.send_json({
            "ok": True,
            "data": {
                "lottery_type_id": lottery_type_id,
                "start_issue": start_issue,
                "end_issue": end_issue,
                "draw_count": len(target_draws),
                "total_affected": total_affected,
                "tables_affected": len(affected_tables),
                "per_table": per_table_summary,
                "draws": draw_reports,
            },
        })


def get_backfill_logs(ctx: RequestContext) -> None:
    """查询回补检查/生成事件日志。

    查询参数：
    - lottery_type_id: 彩种 ID（可选）
    - period: 期号模糊匹配（可选，如 2026133）
    - action: 动作筛选（可选，如 skipped/generated/error）
    - date_from / date_to: 时间范围（可选）
    - page / page_size: 分页（默认 1 / 30）
    """
    lottery_type_id = ctx.query_value("lottery_type_id")
    period = ctx.query_value("period") or ""
    action = ctx.query_value("action") or ""
    date_from = ctx.query_value("date_from") or ""
    date_to = ctx.query_value("date_to") or ""
    page = max(1, int(ctx.query_value("page", "1") or "1"))
    page_size = min(200, max(1, int(ctx.query_value("page_size", "30") or "30")))

    conditions: list[str] = ["logger_name = 'prediction.backfill'"]
    params: list[Any] = []

    if lottery_type_id not in (None, ""):
        conditions.append("lottery_type_id = ?")
        params.append(int(lottery_type_id))
    if period:
        conditions.append("message LIKE ?")
        params.append(f"%期号={period}%")
    if action:
        conditions.append("message LIKE ?")
        params.append(f"%动作={action}%")
    if date_from:
        conditions.append("created_at >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("created_at <= ?")
        params.append(date_to)

    where = " AND ".join(conditions)
    offset = max(0, page - 1) * page_size

    with connect(ctx.db_path) as conn:
        total = int(
            conn.execute(
                f"SELECT COUNT(*) AS cnt FROM error_logs WHERE {where}",
                params,
            ).fetchone()["cnt"]
            or 0
        )
        rows = conn.execute(
            f"SELECT id, created_at, level, message, lottery_type_id "
            f"FROM error_logs WHERE {where} "
            f"ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()

    items = [dict(r) for r in rows]
    ctx.send_json({
        "ok": True,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        },
    })
