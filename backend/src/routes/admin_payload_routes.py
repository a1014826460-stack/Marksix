from __future__ import annotations

from admin.payload import (
    delete_mode_payload_row,
    list_mode_payload_rows,
    update_mode_payload_row,
)
from app_http.request_context import RequestContext
from app_http.router import Router
from app_http.security import MAX_ADMIN_LIST_LIMIT, parse_bounded_int
from app_http.auth import require_admin
from app_http.site_context import (
    extract_site_web_value,
    parse_site_route_context,
    resolve_site_context,
    validate_web_matches_site,
)
from domains.prediction.mode_payload_service import ensure_mode_payload_row_belongs_to_site


def register(router: Router) -> None:
    router.add_regex(None, r"^/api/admin/sites/\d+/mode-payload/[^/]+$", site_payload_detail, guard=require_admin)
    router.add_regex(None, r"^/api/admin/sites/\d+/mode-payload/[^/]+/[^/]+$", site_payload_detail, guard=require_admin)


def site_payload_detail(ctx: RequestContext) -> None:
    site_ctx = parse_site_route_context(ctx)
    parts = site_ctx.parts
    if len(parts) < 7 or parts[5] != "mode-payload":
        raise KeyError("route not found")

    table_name = str(parts[6])
    query_source = ctx.query_value("source", "public") or "public"
    body = ctx.read_json() if ctx.method in {"POST", "PUT", "PATCH"} else {}
    current_site = resolve_site_context(ctx.db_path, path_site_id=site_ctx.site_id, query=ctx.query, body=body)
    validate_web_matches_site(current_site, extract_site_web_value(ctx.query, body))
    web_filter = str(current_site.web_id)

    if len(parts) == 7 and ctx.method == "GET":
        ctx.send_json(
            list_mode_payload_rows(
                ctx.db_path,
                table_name,
                type_filter=ctx.query_value("type", "") or "",
                web_filter=web_filter,
                page=parse_bounded_int(
                    ctx.query_value("page", "1"),
                    default=1,
                    maximum=MAX_ADMIN_LIST_LIMIT,
                    field_name="page",
                ),
                page_size=parse_bounded_int(
                    ctx.query_value("page_size", "50"),
                    default=50,
                    maximum=MAX_ADMIN_LIST_LIMIT,
                    field_name="page_size",
                ),
                search=ctx.query_value("search", "") or "",
                source=query_source,
            )
        )
        return

    if len(parts) == 8 and ctx.method in {"PUT", "PATCH"}:
        ensure_mode_payload_row_belongs_to_site(
            ctx.db_path,
            table_name,
            parts[7],
            source=query_source,
            site_web_id=current_site.web_id,
        )
        body.setdefault("web", current_site.web_id)
        body.setdefault("web_id", current_site.web_id)
        ctx.send_json(
            update_mode_payload_row(
                ctx.db_path,
                table_name,
                parts[7],
                body,
                source=query_source,
            )
        )
        return

    if len(parts) == 8 and ctx.method == "DELETE":
        ensure_mode_payload_row_belongs_to_site(
            ctx.db_path,
            table_name,
            parts[7],
            source=query_source,
            site_web_id=current_site.web_id,
        )
        delete_mode_payload_row(
            ctx.db_path,
            table_name,
            parts[7],
            source=query_source,
        )
        ctx.send_json({"ok": True})
        return

    raise KeyError("site route not found")

