from __future__ import annotations

from app_http.request_context import RequestContext
from app_http.router import Router
from app_http.auth import require_admin
from domains.dashboard import get_dashboard_overview
from domains.scheduler.service import retry_failed_scheduler_task
from routes.admin_result_response import gate_admin_result_response, mark_restricted_draw_numbers


def register(router: Router) -> None:
    router.add("GET", "/api/admin/dashboard", overview, guard=require_admin)
    router.add_prefix("POST", "/api/admin/dashboard/scheduler-tasks/", retry_scheduler_task, guard=require_admin)


def overview(ctx: RequestContext) -> None:
    result = gate_admin_result_response(ctx, get_dashboard_overview(ctx.db_path))
    ctx.send_json(mark_restricted_draw_numbers(result))


def retry_scheduler_task(ctx: RequestContext) -> None:
    ctx.response.set_header("Cache-Control", "no-store")
    parts = ctx.path.rstrip("/").split("/")
    if len(parts) != 7 or parts[-1] != "retry":
        raise KeyError("接口不存在")
    result = gate_admin_result_response(ctx, {"task": retry_failed_scheduler_task(ctx.db_path, task_id=int(parts[-2]))})
    ctx.send_json(mark_restricted_draw_numbers(result))
