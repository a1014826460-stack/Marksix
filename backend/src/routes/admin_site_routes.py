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
    sync_site_prediction_modules_for_admin,
    update_site_prediction_module,
)
from domains.sites.service import get_site, list_sites, save_site, delete_site
from app_http.auth import require_admin, require_site_generation_access, require_super_admin
from app_http.request_context import RequestContext
from app_http.router import Router
from app_http.site_context import (
    extract_site_web_value,
    parse_site_route_context,
    resolve_site_context,
    validate_web_matches_site,
)
from deprecated.site_fetch_chain import deprecated_site_fetch_payload

from datetime import datetime, timezone
from secrets import token_hex

from domains.scheduler.service import enqueue_manual_job


def register(router: Router) -> None:
    router.add("GET", "/api/admin/sites", list_site_routes, guard=require_admin)
    router.add("POST", "/api/admin/sites", create_site, guard=require_super_admin)
    router.add_regex(None, r"^/api/admin/sites/\d+$", site_detail, guard=require_admin)
    router.add_regex("POST", r"^/api/admin/sites/\d+/fetch$", site_detail, guard=require_admin)
    router.add_regex(None, r"^/api/admin/sites/\d+/prediction-modules$", site_detail, guard=require_admin)
    router.add_regex(None, r"^/api/admin/sites/\d+/prediction-modules/[^/]+$", site_detail, guard=require_admin)


def list_site_routes(ctx: RequestContext) -> None:
    ctx.send_json({"sites": list_sites(ctx.db_path)})


def create_site(ctx: RequestContext) -> None:
    ctx.send_json({"site": save_site(ctx.db_path, ctx.read_json())}, HTTPStatus.CREATED)


def site_detail(ctx: RequestContext) -> None:
    site_ctx = parse_site_route_context(ctx)
    parts = site_ctx.parts
    site_id = site_ctx.site_id
    current_site = resolve_site_context(ctx.db_path, path_site_id=site_id)
    current_user = ctx.state.get("current_user")
    from domains.sites.permissions import can_access_site
    if not can_access_site(current_user, site_id, db_path=ctx.db_path):
        from core.errors import ForbiddenError
        raise ForbiddenError("当前账号没有访问该站点的权限")

    if len(parts) == 5:
        if ctx.method == "GET":
            ctx.send_json({"site": get_site(ctx.db_path, site_id)})
            return
        if ctx.method in {"PUT", "PATCH"}:
            require_super_admin(ctx)
            ctx.send_json({"site": save_site(ctx.db_path, ctx.read_json(), site_id)})
            return
        if ctx.method == "DELETE":
            require_super_admin(ctx)
            delete_site(ctx.db_path, site_id)
            ctx.send_json({"ok": True})
            return

    if len(parts) == 6 and parts[5] == "fetch" and ctx.method == "POST":
        body = ctx.read_json()
        validate_web_matches_site(current_site, extract_site_web_value(ctx.query, body))
        ctx.send_json(deprecated_site_fetch_payload(site_id), HTTPStatus.GONE)
        return

    if len(parts) == 6 and parts[5] == "prediction-modules":
        if ctx.method == "GET":
            ctx.send_json(list_site_prediction_modules(ctx.db_path, site_id))
            return
        if ctx.method == "POST":
            require_site_generation_access(ctx, site_id)
            ctx.send_json(
                {"module": add_site_prediction_module(ctx.db_path, site_id, ctx.read_json())},
                HTTPStatus.CREATED,
            )
            return

    if len(parts) == 7 and parts[5] == "prediction-modules":
        if parts[6] == "sync" and ctx.method == "POST":
            require_site_generation_access(ctx, site_id)
            ctx.send_json(sync_site_prediction_modules_for_admin(ctx.db_path, site_id))
            return
        if parts[6] == "generate-all" and ctx.method == "POST":
            require_site_generation_access(ctx, site_id)
            body = ctx.read_json()
            validate_web_matches_site(current_site, extract_site_web_value(ctx.query, body))
            job_id = enqueue_manual_job(
                ctx.db_path,
                job_type="site_prediction_generate_all",
                payload={"site_id": site_id, "options": body},
                metadata={
                    "site_id": current_site.site_id,
                    "web_id": current_site.web_id,
                    "lottery_type_id": current_site.lottery_type_id,
                    "task_type": "site_prediction_generate_all",
                },
                created_by=str((ctx.state.get("current_user") or {}).get("username") or "unknown"),
                job_id=token_hex(8),
                run_at=datetime.now(timezone.utc).isoformat(),
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
            require_site_generation_access(ctx, site_id)
            body = ctx.read_json()
            ctx.send_json(
                estimate_site_prediction_modules_bulk_delete(ctx.db_path, site_id, body)
            )
            return
        if parts[6] == "bulk-delete" and ctx.method == "DELETE":
            require_site_generation_access(ctx, site_id)
            body = ctx.read_json()
            ctx.send_json(
                bulk_delete_site_prediction_modules(ctx.db_path, site_id, body)
            )
            return
        if parts[6] == "run" and ctx.method == "POST":
            require_site_generation_access(ctx, site_id)
            body = ctx.read_json()
            validate_web_matches_site(current_site, extract_site_web_value(ctx.query, body))
            ctx.send_json(run_site_prediction_module(ctx.db_path, site_id, body))
            return
        if ctx.method in {"PUT", "PATCH"}:
            require_site_generation_access(ctx, site_id)
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
            require_site_generation_access(ctx, site_id)
            delete_site_prediction_module(ctx.db_path, site_id, int(parts[6]))
            ctx.send_json({"ok": True})
            return

    raise KeyError("站点接口不存在")
