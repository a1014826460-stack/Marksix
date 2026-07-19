from __future__ import annotations

from legacy.api import list_legacy_post_images
from utils.build_text_history_mappings import build_text_history_mappings
from utils.normalize_payload_tables import normalize_payload_tables

from app_http.request_context import RequestContext
from app_http.router import Router
from app_http.security import MAX_ADMIN_LIST_LIMIT, parse_bounded_int
from app_http.auth import require_admin

from .common import list_fetch_runs


def register(router: Router, *, default_pc: int, default_web: int, default_type: int) -> None:
    router.add("GET", "/api/admin/fetch-runs", fetch_runs, guard=require_admin)
    router.add("GET", "/api/admin/legacy-images", lambda ctx: legacy_images(ctx, default_pc, default_web, default_type), guard=require_admin)
    router.add("POST", "/api/admin/normalize", normalize, guard=require_admin)
    router.add("POST", "/api/admin/text-mappings", text_mappings, guard=require_admin)


def fetch_runs(ctx: RequestContext) -> None:
    limit = parse_bounded_int(
        ctx.query_value("limit", "20"),
        default=20,
        maximum=MAX_ADMIN_LIST_LIMIT,
        field_name="limit",
    )
    ctx.send_json({"runs": list_fetch_runs(ctx.db_path, limit)})


def legacy_images(ctx: RequestContext, default_pc: int, default_web: int, default_type: int) -> None:
    limit = parse_bounded_int(
        ctx.query_value("limit", "50"),
        default=50,
        maximum=MAX_ADMIN_LIST_LIMIT,
        field_name="limit",
    )
    ctx.send_json(
        {
            "images": list_legacy_post_images(
                ctx.db_path,
                source_pc=default_pc,
                source_web=default_web,
                source_type=default_type,
                limit=limit,
            )
        }
    )


def normalize(ctx: RequestContext) -> None:
    result = normalize_payload_tables(ctx.db_path)
    ctx.send_json({"normalized_tables": len(result), "tables": result})


def text_mappings(ctx: RequestContext) -> None:
    ctx.send_json(build_text_history_mappings(ctx.db_path, rebuild=True))
