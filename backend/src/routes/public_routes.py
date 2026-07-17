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
from domains.sites.service import get_public_notice
from domains.traffic.service import record_traffic_event


def register(router: Router) -> None:
    router.add("GET", "/api/public/site-page", site_page)
    router.add("GET", "/api/public/latest-draw", latest_draw)
    router.add("GET", "/api/public/next-draw-deadline", next_draw_deadline)
    router.add("GET", "/api/public/draw-history", draw_history)
    router.add("GET", "/api/public/current-period", current_period)
    router.add("GET", "/api/public/notice", notice)
    router.add("POST", "/api/public/traffic-events", traffic_events)
    # 旧前端兼容路径
    router.add("GET", "/api/index/notice", notice)


def site_page(ctx: RequestContext) -> None:
    site_id = ctx.query_value("site_id")
    history_limit = int(ctx.query_value("history_limit", "8") or 8)
    lottery_type = ctx.query_value("lottery_type")
    raw_mode_ids = str(ctx.query_value("mode_ids", "") or "").strip()
    mode_ids = []
    if raw_mode_ids:
        for item in raw_mode_ids.split(","):
            item = item.strip()
            if not item:
                continue
            try:
                parsed = int(item)
            except ValueError:
                continue
            if parsed > 0:
                mode_ids.append(parsed)
    ctx.send_json(
        get_public_site_page_data(
            ctx.db_path,
            site_id=int(site_id) if site_id not in (None, "") else None,
            domain=ctx.query_value("domain"),
            history_limit=history_limit,
            lottery_type_id=int(lottery_type) if lottery_type not in (None, "") else None,
            mode_ids=mode_ids or None,
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


def notice(ctx: RequestContext) -> None:
    """公告弹窗接口。

    根据 web 参数查找对应站点公告，返回前端要求的 { code: 600, data: { content } } 格式。
    code 必须为 600，否则前端会跳过公告展示。
    """
    raw_web = ctx.query_value("web")
    web_id: int | None = None
    if raw_web not in (None, ""):
        try:
            web_id = int(str(raw_web).strip())
        except (ValueError, TypeError):
            pass

    ctx.send_json(get_public_notice(ctx.db_path, web_id))


def _client_ip(ctx: RequestContext) -> str | None:
    forwarded = str(ctx.headers.get("X-Forwarded-For", "") or "").split(",", 1)[0].strip()
    if forwarded:
        return forwarded
    client_address = getattr(ctx.handler, "client_address", None)
    if isinstance(client_address, tuple) and client_address:
        return str(client_address[0])
    return None


def traffic_events(ctx: RequestContext) -> None:
    ctx.send_json(
        record_traffic_event(
            ctx.db_path,
            ctx.body,
            ip_address=_client_ip(ctx),
            user_agent=str(ctx.headers.get("User-Agent", "") or ""),
        )
    )
