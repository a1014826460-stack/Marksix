from __future__ import annotations

from http import HTTPStatus

from domains.prediction.service import (
    bulk_generate_site_predictions,
    add_site_prediction_module,
    bulk_delete_site_prediction_modules,
    delete_site_prediction_module,
    estimate_site_prediction_modules_bulk_delete,
    list_site_prediction_modules,
    run_prediction as run_site_prediction_module,
    update_site_prediction_module,
)
from domains.sites.service import get_site, list_sites, save_site, delete_site
from helpers import parse_bool
from app_http.auth import require_generation_access
from app_http.request_context import RequestContext
from app_http.router import Router
from app_http.site_context import (
    extract_site_web_value,
    parse_site_route_context,
    resolve_site_context,
    validate_web_matches_site,
)

from .common import fetch_site_data, start_background_job


def register(router: Router) -> None:
    router.add("GET", "/api/admin/sites", list_site_routes)
    router.add("POST", "/api/admin/sites", create_site)
    router.add_regex(None, r"^/api/admin/sites/\d+$", site_detail)
    router.add_regex("POST", r"^/api/admin/sites/\d+/fetch$", site_detail)
    router.add_regex(None, r"^/api/admin/sites/\d+/prediction-modules$", site_detail)
    router.add_regex(None, r"^/api/admin/sites/\d+/prediction-modules/[^/]+$", site_detail)


def list_site_routes(ctx: RequestContext) -> None:
    ctx.send_json({"sites": list_sites(ctx.db_path)})


def create_site(ctx: RequestContext) -> None:
    ctx.send_json({"site": save_site(ctx.db_path, ctx.read_json())}, HTTPStatus.CREATED)


def site_detail(ctx: RequestContext) -> None:
    site_ctx = parse_site_route_context(ctx)
    parts = site_ctx.parts
    site_id = site_ctx.site_id
    current_site = resolve_site_context(ctx.db_path, path_site_id=site_id)

    if len(parts) == 5:
        if ctx.method == "GET":
            ctx.send_json({"site": get_site(ctx.db_path, site_id)})
            return
        if ctx.method in {"PUT", "PATCH"}:
            ctx.send_json({"site": save_site(ctx.db_path, ctx.read_json(), site_id)})
            return
        if ctx.method == "DELETE":
            delete_site(ctx.db_path, site_id)
            ctx.send_json({"ok": True})
            return

    if len(parts) == 6 and parts[5] == "fetch" and ctx.method == "POST":
        body = ctx.read_json()
        validate_web_matches_site(current_site, extract_site_web_value(ctx.query, body))
        result = fetch_site_data(
            ctx.db_path,
            site_id,
            normalize_after=parse_bool(body.get("normalize"), True),
            build_text_mappings_after=parse_bool(body.get("build_text_mappings"), True),
        )
        ctx.send_json(result)
        return

    if len(parts) == 6 and parts[5] == "prediction-modules":
        if ctx.method == "GET":
            ctx.send_json(list_site_prediction_modules(ctx.db_path, site_id))
            return
        if ctx.method == "POST":
            ctx.send_json(
                {"module": add_site_prediction_module(ctx.db_path, site_id, ctx.read_json())},
                HTTPStatus.CREATED,
            )
            return

    if len(parts) == 7 and parts[5] == "prediction-modules":
        if parts[6] == "generate-all" and ctx.method == "POST":
            require_generation_access(ctx)
            body = ctx.read_json()
            validate_web_matches_site(current_site, extract_site_web_value(ctx.query, body))
            job_id = start_background_job(
                bulk_generate_site_predictions,
                ctx.db_path,
                site_id,
                body,
                metadata={
                    "site_id": current_site.site_id,
                    "web_id": current_site.web_id,
                    "lottery_type_id": current_site.lottery_type_id,
                    "task_type": "site_prediction_generate_all",
                    "created_by": (ctx.state.get("current_user") or {}).get("username", "unknown"),
                },
            )
            ctx.send_json(
                {
                    "ok": True,
                    "job_id": job_id,
                    "message": "批量生成已放入后台执行，可通过 /api/admin/jobs/{job_id} 查询进度",
                }
            )
            return
        if parts[6] == "bulk-delete-estimate" and ctx.method == "POST":
            require_generation_access(ctx)
            body = ctx.read_json()
            ctx.send_json(
                estimate_site_prediction_modules_bulk_delete(ctx.db_path, site_id, body)
            )
            return
        if parts[6] == "bulk-delete" and ctx.method == "DELETE":
            require_generation_access(ctx)
            body = ctx.read_json()
            ctx.send_json(
                bulk_delete_site_prediction_modules(ctx.db_path, site_id, body)
            )
            return
        if parts[6] == "run" and ctx.method == "POST":
            require_generation_access(ctx)
            body = ctx.read_json()
            validate_web_matches_site(current_site, extract_site_web_value(ctx.query, body))
            ctx.send_json(run_site_prediction_module(ctx.db_path, site_id, body))
            return
        if ctx.method in {"PUT", "PATCH"}:
            ctx.send_json(
                {
                    "module": update_site_prediction_module(
                        ctx.db_path,
                        site_id,
                        int(parts[6]),
                        ctx.read_json(),
                    )
                }
            )
            return
        if ctx.method == "DELETE":
            delete_site_prediction_module(ctx.db_path, site_id, int(parts[6]))
            ctx.send_json({"ok": True})
            return

    raise KeyError("站点接口不存在")
