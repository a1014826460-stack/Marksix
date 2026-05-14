from __future__ import annotations

import time

from public.api import (
    get_current_period,
    get_draw_history,
    get_public_latest_draw,
    get_public_next_draw_deadline,
    get_public_site_page_data,
)

from app_http.site_context import resolve_site_context
from app_http.request_context import RequestContext
from app_http.router import Router


def register(router: Router) -> None:
    router.add("GET", "/api/public/site-page", site_page)
    router.add("GET", "/api/public/latest-draw", latest_draw)
    router.add("GET", "/api/public/next-draw-deadline", next_draw_deadline)
    router.add("GET", "/api/public/draw-history", draw_history)
    router.add("GET", "/api/public/current-period", current_period)


def site_page(ctx: RequestContext) -> None:
    site_id = ctx.query_value("site_id")
    history_limit = int(ctx.query_value("history_limit", "8") or 8)
    ctx.send_json(
        get_public_site_page_data(
            ctx.db_path,
            site_id=int(site_id) if site_id not in (None, "") else None,
            domain=ctx.query_value("domain"),
            history_limit=history_limit,
        )
    )


def latest_draw(ctx: RequestContext) -> None:
    site_id = ctx.query_value("site_id")
    if site_id not in (None, ""):
        site_ctx = resolve_site_context(ctx.db_path, path_site_id=int(site_id), query=ctx.query)
        lottery_type = int(site_ctx.lottery_type_id or 1)
    else:
        lottery_type = int(ctx.query_value("lottery_type", "1") or 1)
    ctx.send_json(get_public_latest_draw(ctx.db_path, lottery_type))


def next_draw_deadline(ctx: RequestContext) -> None:
    """
    返回下一期开奖截止时间和服务器当前时间，单位为秒级时间戳
    - args:
        - site_id: 可选，站点ID，如果提供则根据站点配置的彩票类型返回截止时间，否则根据lottery_type参数返回截止时间
        - lottery_type: 可选，彩票类型ID，默认为3（双色球），仅在site_id未提供时
    - return:
        - draw_deadline: 下一期开奖截止时间，单位为毫秒级时间戳
        - server_time: 服务器当前时间，单位为秒级时间戳
    """
    site_id = ctx.query_value("site_id")
    if site_id not in (None, ""):
        site_ctx = resolve_site_context(ctx.db_path, path_site_id=int(site_id), query=ctx.query)
        lottery_type = int(site_ctx.lottery_type_id or 3)
    else:
        lottery_type = int(ctx.query_value("lottery_type", "3") or 3)
    payload = get_public_next_draw_deadline(ctx.db_path, lottery_type)
    payload["server_time"] = str(int(time.time()))
    ctx.send_json(payload)


def draw_history(ctx: RequestContext) -> None:
    site_id = ctx.query_value("site_id")
    if site_id not in (None, ""):
        site_ctx = resolve_site_context(ctx.db_path, path_site_id=int(site_id), query=ctx.query)
        lottery_type = int(site_ctx.lottery_type_id or 3)
    else:
        lottery_type = int(ctx.query_value("lottery_type", "3") or 3)
    year = int(ctx.query_value("year", "0") or 0) or None
    sort = ctx.query_value("sort", "l") or "l"
    ctx.send_json(get_draw_history(ctx.db_path, lottery_type, year, sort))


def current_period(ctx: RequestContext) -> None:
    lottery_type = int(ctx.query_value("lottery_type", "3") or 3)
    ctx.send_json(get_current_period(ctx.db_path, lottery_type))
