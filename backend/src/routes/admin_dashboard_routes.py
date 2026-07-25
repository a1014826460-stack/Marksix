from __future__ import annotations

from app_http.request_context import RequestContext
from app_http.router import Router
from app_http.auth import require_admin
from domains.dashboard import get_dashboard_overview
from domains.scheduler.service import retry_failed_scheduler_task


def register(router: Router) -> None:
    router.add("GET", "/api/admin/dashboard", overview, guard=require_admin)
    router.add_prefix("POST", "/api/admin/dashboard/scheduler-tasks/", retry_scheduler_task, guard=require_admin)


def overview(ctx: RequestContext) -> None:
    ctx.send_json(get_dashboard_overview(ctx.db_path))


def retry_scheduler_task(ctx: RequestContext) -> None:
    parts = ctx.path.rstrip("/").split("/")
    if len(parts) != 7 or parts[-1] != "retry":
        raise KeyError("接口不存在")
    ctx.send_json({"task": retry_failed_scheduler_task(ctx.db_path, task_id=int(parts[-2]))})
