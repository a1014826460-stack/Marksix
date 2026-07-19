from __future__ import annotations

from domains.logs.service import query_backfill_logs
from domains.prediction.backfill_service import (
    normalize_target_tables,
    run_backfill_predictions,
)

from app_http.auth import require_admin
from app_http.request_context import RequestContext
from app_http.router import Router
from app_http.security import MAX_ADMIN_LIST_LIMIT, parse_bounded_int


def register(router: Router) -> None:
    router.add(
        "POST",
        "/api/admin/backfill-predictions",
        backfill_predictions,
        guard=require_admin,
    )
    router.add(
        "GET",
        "/api/admin/backfill-predictions/logs",
        get_backfill_logs,
        guard=require_admin,
    )


def backfill_predictions(ctx: RequestContext) -> None:
    body = ctx.read_json()
    lottery_type_id = int(body.get("lottery_type_id") or 3)
    start_issue = str(body.get("start_issue") or "")
    end_issue = str(body.get("end_issue") or "")
    recent_count = body.get("recent_count")
    raw_table_names = body.get("table_names") or []

    try:
        target_tables = normalize_target_tables(raw_table_names)
        result = run_backfill_predictions(
            ctx.db_path,
            lottery_type_id=lottery_type_id,
            start_issue=start_issue,
            end_issue=end_issue,
            recent_count=int(recent_count) if recent_count is not None else None,
            target_tables=target_tables,
        )
    except ValueError as error:
        ctx.send_json({"ok": False, "error": str(error)}, 400)
        return

    ctx.send_json({"ok": True, "data": result})


def get_backfill_logs(ctx: RequestContext) -> None:
    lottery_type_id = ctx.query_value("lottery_type_id")
    period = ctx.query_value("period") or ""
    action = ctx.query_value("action") or ""
    date_from = ctx.query_value("date_from") or ""
    date_to = ctx.query_value("date_to") or ""
    page = parse_bounded_int(
        ctx.query_value("page", "1"),
        default=1,
        maximum=MAX_ADMIN_LIST_LIMIT,
        field_name="page",
    )
    page_size = parse_bounded_int(
        ctx.query_value("page_size", "30"),
        default=30,
        maximum=MAX_ADMIN_LIST_LIMIT,
        field_name="page_size",
    )
    result = query_backfill_logs(
        ctx.db_path,
        lottery_type_id=int(lottery_type_id) if lottery_type_id not in (None, "") else None,
        period=period,
        action=action,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    ctx.send_json({"ok": True, "data": result})
