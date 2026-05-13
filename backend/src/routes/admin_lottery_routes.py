from __future__ import annotations

import re

from http import HTTPStatus

from admin.crud import delete_lottery_type, list_lottery_types, save_lottery_type
from crawler.crawler_service import run_crawl_only
from app_http.auth import require_generation_access
from app_http.request_context import RequestContext
from app_http.router import Router

from .common import crawl_and_generate, start_background_job


def register(router: Router) -> None:
    router.add("GET", "/api/admin/lottery-types", list_types)
    router.add("POST", "/api/admin/lottery-types", create_type)
    router.add_regex("POST", r"^/api/admin/lottery-types/\d+/crawl-only$", crawl_only)
    router.add_regex("POST", r"^/api/admin/lottery-types/\d+/crawl-and-generate$", crawl_and_generate_route)
    router.add_prefix(None, "/api/admin/lottery-types/", lottery_type_detail)


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
    job_id = start_background_job(crawl_and_generate, ctx.db_path, lt_id)
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
