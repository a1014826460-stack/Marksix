from __future__ import annotations

from domains.logs import service as logs_service

from http import HTTPStatus
from app_http.request_context import RequestContext
from app_http.router import Router
from app_http.security import MAX_ADMIN_LIST_LIMIT, parse_bounded_int
from app_http.auth import require_admin


def register(router: Router) -> None:
    router.add("GET", "/api/admin/logs/modules", modules, guard=require_admin)
    router.add("GET", "/api/admin/logs/levels", levels, guard=require_admin)
    router.add("GET", "/api/admin/logs/stats", stats, guard=require_admin)
    router.add("POST", "/api/admin/logs/cleanup", cleanup, guard=require_admin)
    router.add("GET", "/api/admin/logs/export", export_logs, guard=require_admin)
    router.add("GET", "/api/admin/logs", list_logs, guard=require_admin)
    router.add_prefix("GET", "/api/admin/logs/", log_detail, guard=require_admin)


def modules(ctx: RequestContext) -> None:
    ctx.send_json({"modules": logs_service.get_log_modules(ctx.db_path)})


def levels(ctx: RequestContext) -> None:
    ctx.send_json({"levels": logs_service.get_log_levels(ctx.db_path)})


def stats(ctx: RequestContext) -> None:
    ctx.send_json(logs_service.get_log_stats(ctx.db_path))


def cleanup(ctx: RequestContext) -> None:
    result = logs_service.trigger_log_cleanup(ctx.db_path)
    ctx.send_json({"ok": True, **result})


def export_logs(ctx: RequestContext) -> None:
    rows = logs_service.export_error_logs(
        ctx.db_path,
        level=ctx.query_value("level", "") or "",
        module=ctx.query_value("module", "") or "",
        keyword=ctx.query_value("keyword", "") or "",
        date_from=ctx.query_value("date_from", "") or "",
        date_to=ctx.query_value("date_to", "") or "",
    )
    ctx.send_json({"rows": rows, "total": len(rows)})


def log_detail(ctx: RequestContext) -> None:
    if ctx.path in {
        "/api/admin/logs/modules",
        "/api/admin/logs/levels",
        "/api/admin/logs/stats",
        "/api/admin/logs/export",
    }:
        raise KeyError("接口不存在")
    log_id_str = ctx.path.split("/")[-1]
    if not log_id_str.isdigit():
        raise KeyError("接口不存在")
    detail = logs_service.get_log_detail(ctx.db_path, int(log_id_str))
    if not detail:
        ctx.send_error_json(HTTPStatus.NOT_FOUND, f"log_id={log_id_str} 不存在")
        return
    ctx.send_json(detail)


def list_logs(ctx: RequestContext) -> None:
    result = logs_service.query_error_logs(
        ctx.db_path,
        page=parse_bounded_int(
            ctx.query_value("page", "1"),
            default=1,
            maximum=MAX_ADMIN_LIST_LIMIT,
            field_name="page",
        ),
        page_size=parse_bounded_int(
            ctx.query_value("page_size", "30"),
            default=30,
            maximum=MAX_ADMIN_LIST_LIMIT,
            field_name="page_size",
        ),
        level=ctx.query_value("level", "") or "",
        module=ctx.query_value("module", "") or "",
        keyword=ctx.query_value("keyword", "") or "",
        date_from=ctx.query_value("date_from", "") or "",
        date_to=ctx.query_value("date_to", "") or "",
        user_id=ctx.query_value("user_id", "") or "",
        site_id=ctx.query_value("site_id", "") or "",
        web_id=ctx.query_value("web_id", "") or "",
        lottery_type_id=ctx.query_value("lottery_type_id", "") or "",
        year=ctx.query_value("year", "") or "",
        term=ctx.query_value("term", "") or "",
        task_type=ctx.query_value("task_type", "") or "",
        task_key=ctx.query_value("task_key", "") or "",
        path=ctx.query_value("path", "") or "",
    )
    ctx.send_json(result)
