from __future__ import annotations

from logger import (
    export_error_logs,
    get_error_log_detail,
    get_log_levels,
    get_log_modules,
    get_log_stats,
    query_error_logs,
    trigger_cleanup,
)

from http import HTTPStatus
from http.request_context import RequestContext
from http.router import Router


def register(router: Router) -> None:
    router.add("GET", "/api/admin/logs/modules", modules)
    router.add("GET", "/api/admin/logs/levels", levels)
    router.add("GET", "/api/admin/logs/stats", stats)
    router.add("POST", "/api/admin/logs/cleanup", cleanup)
    router.add("GET", "/api/admin/logs/export", export_logs)
    router.add("GET", "/api/admin/logs", list_logs)
    router.add_prefix("GET", "/api/admin/logs/", log_detail)


def modules(ctx: RequestContext) -> None:
    ctx.send_json({"modules": get_log_modules(ctx.db_path)})


def levels(ctx: RequestContext) -> None:
    ctx.send_json({"levels": get_log_levels(ctx.db_path)})


def stats(ctx: RequestContext) -> None:
    ctx.send_json(get_log_stats(ctx.db_path))


def cleanup(ctx: RequestContext) -> None:
    result = trigger_cleanup()
    ctx.send_json({"ok": True, **result})


def export_logs(ctx: RequestContext) -> None:
    rows = export_error_logs(
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
    detail = get_error_log_detail(ctx.db_path, int(log_id_str))
    if not detail:
        ctx.send_error_json(HTTPStatus.NOT_FOUND, f"log_id={log_id_str} 不存在")
        return
    ctx.send_json(detail)


def list_logs(ctx: RequestContext) -> None:
    result = query_error_logs(
        ctx.db_path,
        page=int(ctx.query_value("page", "1") or 1),
        page_size=min(int(ctx.query_value("page_size", "30") or 30), 200),
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
