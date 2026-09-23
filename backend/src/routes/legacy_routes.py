from __future__ import annotations

import hashlib
import re

from legacy.api import get_legacy_current_term, list_legacy_post_images, load_legacy_mode_rows

from app_http.request_context import RequestContext
from app_http.router import Router
from app_http.security import MAX_LEGACY_LIST_LIMIT, parse_bounded_int
from db import connect


# 旧站每次页面加载会并发调用几十个 /api/kaijiang/* 端点，单个回源实测 2.7～2.8 秒。
# 这些参数只影响缓存键，不影响业务语义。
_LEGACY_SNAPSHOT_IGNORED_PARAMS = frozenset({"_", "_ts", "callback", "cb"})
_LEGACY_SELECTOR_TOKEN_RE = re.compile(r"[^A-Za-z0-9._-]")


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
        from cache.prediction_snapshots import KIND_LEGACY, read_through

        target = _legacy_kaijiang_snapshot_target(ctx)
        if target is None:
            with connect(ctx.db_path) as conn:
                result = handle_frontend_kaijiang_api(ctx.path, ctx.query, conn)
            ctx.send_json(result)
            return

        site_ref, lottery_type_id, selector = target

        def build() -> dict:
            with connect(ctx.db_path) as conn:
                return handle_frontend_kaijiang_api(ctx.path, ctx.query, conn)

        ctx.send_json(
            read_through(
                ctx.state.get("prediction_snapshots"),
                kind=KIND_LEGACY,
                site_ref=site_ref,
                lottery_type_id=lottery_type_id,
                selector=selector,
                builder=build,
                db_path=ctx.db_path,
            )
        )

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
    limit = parse_bounded_int(
        ctx.query_value("limit", "20"),
        default=20,
        maximum=MAX_LEGACY_LIST_LIMIT,
        field_name="limit",
    )
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


def _legacy_kaijiang_snapshot_target(ctx: RequestContext) -> tuple[str, int, str] | None:
    """Derive (site_ref, lottery_type_id, selector) for a cacheable kaijiang call.

    返回 ``None`` 表示这次请求不适合走快照（curTerm、缺少 web/type/num、参数非法），
    调用方按原有路径直接查库。
    """
    endpoint = str(ctx.path).rsplit("/", 1)[-1].strip()
    if not endpoint or endpoint.lower() == "curterm":
        return None
    token = _LEGACY_SELECTOR_TOKEN_RE.sub("", endpoint)
    if not token:
        return None

    query = ctx.query if isinstance(ctx.query, dict) else {}
    web_raw = _first_query_value(query, "web")
    type_raw = _first_query_value(query, "type")
    num_raw = _first_query_value(query, "num")
    if web_raw in (None, "") or type_raw in (None, "") or num_raw in (None, ""):
        return None
    try:
        web_id = int(str(web_raw).strip())
        lottery_type = int(str(type_raw).strip())
    except (TypeError, ValueError):
        return None
    if web_id <= 0 or lottery_type <= 0:
        return None

    parts: list[str] = []
    for key in sorted(query):
        if key in _LEGACY_SNAPSHOT_IGNORED_PARAMS:
            continue
        values = query[key]
        if isinstance(values, (list, tuple)):
            text = ",".join(str(item) for item in values)
        else:
            text = str(values)
        parts.append(f"{key}={text}")
    digest = hashlib.sha256("&".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"web{web_id}", lottery_type, f"{token}-{digest}"


def _first_query_value(query: dict, key: str) -> str | None:
    values = query.get(key)
    if isinstance(values, (list, tuple)):
        return str(values[0]) if values else None
    if values is None:
        return None
    return str(values)


def module_rows(ctx: RequestContext) -> None:
    from cache.prediction_snapshots import KIND_LEGACY_ROWS, read_through

    modes_id = int(ctx.query_value("modes_id", "0") or 0)
    if modes_id <= 0:
        raise ValueError("modes_id 必须为正整数")
    web_value = ctx.query_value("web")
    type_raw = ctx.query_value("type")
    limit = parse_bounded_int(
        ctx.query_value("limit", "10"),
        default=10,
        maximum=MAX_LEGACY_LIST_LIMIT,
        field_name="limit",
    )
    web_id = int(web_value) if web_value not in (None, "") else None
    type_value = int(type_raw) if type_raw not in (None, "") else None

    # 这是旧站页面实际调用的热路径：前端 /api/kaijiang/<endpoint> 会转成
    # /api/legacy/module-rows?modes_id=&limit=&web=&type=，一页几十次跨节点请求。
    if web_id is None or type_value is None or web_id <= 0 or type_value <= 0:
        ctx.send_json(
            load_legacy_mode_rows(
                ctx.db_path,
                modes_id=modes_id,
                limit=limit,
                web=web_id,
                type_value=type_value,
            )
        )
        return

    def build() -> dict:
        return load_legacy_mode_rows(
            ctx.db_path,
            modes_id=modes_id,
            limit=limit,
            web=web_id,
            type_value=type_value,
        )

    selector = f"rows-{modes_id}-{limit}-{_stable_digest({'web': web_id, 'type': type_value})}"
    ctx.send_json(
        read_through(
            ctx.state.get("prediction_snapshots"),
            kind=KIND_LEGACY_ROWS,
            site_ref=f"web{web_id}",
            lottery_type_id=type_value,
            selector=selector,
            builder=build,
            db_path=ctx.db_path,
        )
    )


def _stable_digest(values: dict) -> str:
    joined = "&".join(f"{key}={values[key]}" for key in sorted(values))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:12]
