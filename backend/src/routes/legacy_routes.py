from __future__ import annotations

from legacy.api import get_legacy_current_term, list_legacy_post_images, load_legacy_mode_rows

from http.request_context import RequestContext
from http.router import Router


def register(router: Router, *, default_pc: int, default_web: int, default_type: int) -> None:
    router.add("GET", "/api/legacy/current-term", current_term)
    router.add(
        "GET",
        "/api/legacy/post-list",
        lambda ctx: post_list(ctx, default_pc=default_pc, default_web=default_web, default_type=default_type),
    )
    router.add("GET", "/api/legacy/module-rows", module_rows)


def current_term(ctx: RequestContext) -> None:
    lottery_type_id = int(ctx.query_value("lottery_type_id", "1") or 1)
    ctx.send_json(get_legacy_current_term(ctx.db_path, lottery_type_id))


def post_list(ctx: RequestContext, *, default_pc: int, default_web: int, default_type: int) -> None:
    pc_raw = ctx.query_value("pc", str(default_pc))
    web_raw = ctx.query_value("web", str(default_web))
    type_raw = ctx.query_value("type", str(default_type))
    limit = int(ctx.query_value("limit", "20") or 20)
    ctx.send_json(
        {
            "data": list_legacy_post_images(
                ctx.db_path,
                source_pc=int(pc_raw) if pc_raw not in (None, "") else None,
                source_web=int(web_raw) if web_raw not in (None, "") else None,
                source_type=int(type_raw) if type_raw not in (None, "") else None,
                limit=limit,
            )
        }
    )


def module_rows(ctx: RequestContext) -> None:
    modes_id = int(ctx.query_value("modes_id", "0") or 0)
    if modes_id <= 0:
        raise ValueError("modes_id 必须为正整数")
    web_value = ctx.query_value("web")
    type_raw = ctx.query_value("type")
    limit = int(ctx.query_value("limit", "10") or 10)
    ctx.send_json(
        load_legacy_mode_rows(
            ctx.db_path,
            modes_id=modes_id,
            limit=limit,
            web=int(web_value) if web_value not in (None, "") else None,
            type_value=int(type_raw) if type_raw not in (None, "") else None,
        )
    )
