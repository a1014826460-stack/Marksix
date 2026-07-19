from __future__ import annotations

import re
from datetime import datetime, timezone
from secrets import token_hex

from http import HTTPStatus

from admin.crud import delete_lottery_type, list_lottery_types, save_lottery_type
from crawler.crawler_service import run_crawl_only
from app_http.auth import require_admin, require_generation_access
from app_http.request_context import RequestContext
from app_http.router import Router

from domains.scheduler.service import enqueue_manual_job


def register(router: Router) -> None:
    router.add("GET", "/api/admin/lottery-types", list_types, guard=require_admin)
    router.add("POST", "/api/admin/lottery-types", create_type, guard=require_admin)
    router.add_regex("POST", r"^/api/admin/lottery-types/\d+/crawl-only$", crawl_only, guard=require_admin)
    router.add_regex("POST", r"^/api/admin/lottery-types/\d+/crawl-and-generate$", crawl_and_generate_route, guard=require_admin)
    router.add_prefix(None, "/api/admin/lottery-types/", lottery_type_detail, guard=require_admin)


def list_types(ctx: RequestContext) -> None:
    ctx.send_json({"lottery_types": list_lottery_types(ctx.db_path)})


def create_type(ctx: RequestContext) -> None:
    ctx.send_json({"lottery_type": save_lottery_type(ctx.db_path, ctx.read_json())}, HTTPStatus.CREATED)


def crawl_only(ctx: RequestContext) -> None:
    require_generation_access(ctx)
    lt_id = int(ctx.path.split("/")[4])
    ctx.send_json(run_crawl_only(ctx.db_path, lt_id))


def crawl_and_generate_route(ctx: RequestContext) -> None:
    require_generation_access(ctx)
    lt_id = int(ctx.path.split("/")[4])
    job_id = enqueue_manual_job(
        ctx.db_path,
        job_type="crawl_and_generate",
        payload={"lottery_type_id": lt_id},
        metadata={"lottery_type_id": lt_id, "task_type": "crawl_and_generate"},
        created_by=str((ctx.state.get("current_user") or {}).get("username") or "unknown"),
        job_id=token_hex(8),
        run_at=datetime.now(timezone.utc).isoformat(),
    )
    ctx.send_json({"ok": True, "job_id": job_id, "message": f"彩种 {lt_id} 爬取+生成已放入后台执行"})


def lottery_type_detail(ctx: RequestContext) -> None:
    if re.match(r"^/api/admin/lottery-types/\d+/(crawl-only|crawl-and-generate)$", ctx.path):
        raise KeyError("接口不存在")
    lottery_id = int(ctx.path.split("/")[-1])
    if ctx.method in {"PUT", "PATCH"}:
        ctx.send_json({"lottery_type": save_lottery_type(ctx.db_path, ctx.read_json(), lottery_id)})
        return
    if ctx.method == "DELETE":
        delete_lottery_type(ctx.db_path, lottery_id)
        ctx.send_json({"ok": True})
        return
    raise KeyError("接口不存在")
