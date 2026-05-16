from __future__ import annotations

from legacy.api import get_legacy_current_term, list_legacy_post_images, load_legacy_mode_rows

from app_http.request_context import RequestContext
from app_http.router import Router
from db import connect


def register(router: Router, *, default_pc: int, default_web: int, default_type: int) -> None:
    router.add("GET", "/api/legacy/current-term", current_term)
    router.add(
        "GET",
        "/api/legacy/post-list",
        lambda ctx: post_list(ctx, default_pc=default_pc, default_web=default_web, default_type=default_type),
    )
    router.add("GET", "/api/legacy/module-rows", module_rows)

    # 旧前端兼容层：接收 twsaimahui 静态页原始请求
    # /api/kaijiang/* 和 /api/post/getList
    _register_frontend_compat_routes(router, default_pc, default_web, default_type)


def _register_frontend_compat_routes(
    router: Router, default_pc: int, default_web: int, default_type: int
) -> None:
    """注册旧前端兼容层路由。

    这些路由接收 twsaimahui 静态 HTML 页面的原始 AJAX 请求格式，
    把请求委托给 legacy/frontend_compat.py 处理。
    """
    from legacy.frontend_compat import (
        handle_frontend_kaijiang_api,
        handle_frontend_post_api,
    )

    def _kaijiang_handler(ctx: RequestContext) -> None:
        with connect(ctx.db_path) as conn:
            result = handle_frontend_kaijiang_api(ctx.path, ctx.query, conn)
        ctx.send_json(result)

    def _post_handler(ctx: RequestContext) -> None:
        with connect(ctx.db_path) as conn:
            result = handle_frontend_post_api(ctx.path, ctx.query, conn)
        ctx.send_json(result)

    # 注意：这些路由仅作为兜底。
    # 正常请求优先走 Next.js 兼容层 (app/api/kaijiang/[...path]/route.ts)
    # 当 Next.js 层未显式处理时才会代理到此处。
    router.add_prefix("GET", "/api/kaijiang/", _kaijiang_handler)
    router.add("GET", "/api/post/getList", _post_handler)


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
