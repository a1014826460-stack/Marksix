from __future__ import annotations

from admin.payload import (
    delete_mode_payload_row,
    list_mode_payload_rows,
    mode_payload_table_columns,
    mode_payload_table_exists,
    normalize_mode_payload_source,
    normalize_mode_payload_row_id,
    update_mode_payload_row,
    validate_mode_payload_table,
)
from admin.prediction import regenerate_payload_data
from core.errors import ForbiddenError, NotFoundError, ValidationError
from app_http.auth import require_generation_access
from app_http.request_context import RequestContext
from app_http.router import Router
from app_http.site_context import (
    extract_site_web_value,
    parse_site_route_context,
    resolve_site_context,
    validate_web_matches_site,
)
from db import connect, quote_identifier


def register(router: Router) -> None:
    router.add_regex(None, r"^/api/admin/sites/\d+/mode-payload/[^/]+$", site_payload_detail)
    router.add_regex(None, r"^/api/admin/sites/\d+/mode-payload/[^/]+/[^/]+$", site_payload_detail)


def _ensure_row_belongs_to_site(
    ctx: RequestContext,
    *,
    table_name: str,
    row_id: str,
    source: str,
    site_web_id: int,
) -> None:
    normalized_source = normalize_mode_payload_source(source)
    validated_table = validate_mode_payload_table(table_name)
    qualified_table = (
        f'{quote_identifier("created")}.{quote_identifier(validated_table)}'
        if normalized_source == "created"
        else quote_identifier(validated_table)
    )
    normalized_row_id = normalize_mode_payload_row_id(row_id, normalized_source)
    with connect(ctx.db_path) as conn:
        if not mode_payload_table_exists(conn, validated_table, normalized_source):
            raise NotFoundError(f"table not found: {validated_table}")
        columns = set(mode_payload_table_columns(conn, validated_table, normalized_source))
        web_columns = [column_name for column_name in ("web_id", "web") if column_name in columns]
        if not web_columns:
            return
        select_sql = ", ".join(quote_identifier(column_name) for column_name in web_columns)
        row = conn.execute(
            f"SELECT {select_sql} FROM {qualified_table} WHERE id = ?",
            (normalized_row_id,),
        ).fetchone()
        if not row:
            raise NotFoundError(f"row not found: {row_id}")
        for column_name in web_columns:
            if str(row[column_name] or "").strip() == str(site_web_id):
                return
        raise ForbiddenError(
            f"当前站点 web_id={site_web_id} 无权访问其他站点的 mode_payload 行"
        )


def site_payload_detail(ctx: RequestContext) -> None:
    site_ctx = parse_site_route_context(ctx)
    parts = site_ctx.parts
    if len(parts) < 7 or parts[5] != "mode-payload":
        raise KeyError("接口不存在")

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
                page=int(ctx.query_value("page", "1") or 1),
                page_size=int(ctx.query_value("page_size", "50") or 50),
                search=ctx.query_value("search", "") or "",
                source=query_source,
            )
        )
        return

    if len(parts) == 8 and parts[7] == "regenerate" and ctx.method == "POST":
        require_generation_access(ctx)
        ctx.send_json(
            regenerate_payload_data(
                ctx.db_path,
                table_name=table_name,
                mechanism_key=str(body.get("mechanism_key", "")),
                res_code=str(body.get("res_code", "")),
                lottery_type=str(body.get("lottery_type", "3")),
                year=str(body.get("year", "")),
                term=str(body.get("term", "")),
                web_value=str(current_site.web_id),
            )
        )
        return

    if len(parts) == 8 and parts[7] != "regenerate" and ctx.method in {"PUT", "PATCH"}:
        _ensure_row_belongs_to_site(
            ctx,
            table_name=table_name,
            row_id=parts[7],
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

    if len(parts) == 8 and parts[7] != "regenerate" and ctx.method == "DELETE":
        _ensure_row_belongs_to_site(
            ctx,
            table_name=table_name,
            row_id=parts[7],
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

    raise KeyError("站点接口不存在")
