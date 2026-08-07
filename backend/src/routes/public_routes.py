from __future__ import annotations

import time
from typing import Any

from cache.contracts import CacheUnavailable
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
from app_http.security import MAX_PUBLIC_HISTORY_LIMIT, parse_bounded_int
from core.errors import ValidationError
from domains.sites.service import get_public_notice, get_public_site_links
from domains.traffic.service import record_traffic_event


def register(router: Router) -> None:
    router.add("GET", "/api/public/site-page", site_page)
    router.add("GET", "/api/public/latest-draw", latest_draw)
    router.add("GET", "/api/public/next-draw-deadline", next_draw_deadline)
    router.add("GET", "/api/public/draw-history", draw_history)
    router.add("GET", "/api/public/current-period", current_period)
    router.add("GET", "/api/public/notice", notice)
    router.add("GET", "/api/public/site-links", site_links)
    router.add("POST", "/api/public/traffic-events", traffic_events)
    # 旧前端兼容路径
    router.add("GET", "/api/index/notice", notice)


def site_page(ctx: RequestContext) -> None:
    site_id = ctx.query_value("site_id")
    history_limit = parse_bounded_int(
        ctx.query_value("history_limit", "8"),
        default=8,
        maximum=MAX_PUBLIC_HISTORY_LIMIT,
        field_name="history_limit",
    )
    lottery_type = ctx.query_value("lottery_type")
    history_web_start = _parse_optional_history_web_id(ctx.query_value("history_web_start"), "history_web_start")
    history_web_end = _parse_optional_history_web_id(ctx.query_value("history_web_end"), "history_web_end")
    if history_web_start is not None and history_web_end is not None and history_web_end < history_web_start:
        raise ValidationError("history_web_end 不能小于 history_web_start")
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
            history_web_start=history_web_start,
            history_web_end=history_web_end,
        )
    )


def _parse_optional_history_web_id(value: object, field_name: str) -> int | None:
    """Validate the optional shared-history scope before it reaches SQL filters."""
    if value in (None, ""):
        return None
    return parse_bounded_int(
        value,
        default=1,
        maximum=100_000,
        field_name=field_name,
    )


def latest_draw(ctx: RequestContext) -> None:
    site_id = ctx.query_value("site_id")
    if site_id not in (None, ""):
        lottery_type = _resolve_site_lottery_type(ctx, int(site_id))
    else:
        lottery_type = int(ctx.query_value("lottery_type", "1") or 1)
    snapshots = _public_draw_snapshots(ctx)
    if snapshots is not None:
        try:
            cached = snapshots.get_latest_draw(lottery_type)
        except CacheUnavailable:
            cached = None
        if cached is not None:
            ctx.send_json(cached)
            return

    # A just-published result must not wait for a replica to catch up.
    payload = get_public_latest_draw(ctx.write_db_path, lottery_type)
    _backfill_latest_draw(snapshots, lottery_type, payload)
    ctx.send_json(payload)


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
    snapshots = _public_draw_snapshots(ctx)
    if snapshots is not None:
        try:
            cached = snapshots.get_current_period(lottery_type)
        except CacheUnavailable:
            cached = None
        if cached is not None:
            ctx.send_json(cached)
            return

    # Use the primary for a cache miss so the draw publication SLA is preserved.
    payload = get_current_period(ctx.write_db_path, lottery_type)
    _backfill_current_period(snapshots, lottery_type, payload)
    ctx.send_json(payload)


def _public_draw_snapshots(ctx: RequestContext) -> Any | None:
    snapshots = ctx.state.get("public_draw_snapshots")
    if snapshots is None:
        return None
    required = (
        "get_latest_draw",
        "get_current_period",
        "publish_latest_draw",
        "publish_current_period",
    )
    return snapshots if all(callable(getattr(snapshots, name, None)) for name in required) else None


def _resolve_site_lottery_type(ctx: RequestContext, site_id: int) -> int:
    """Resolve a site once from the primary, then retain only its public type."""
    cache = ctx.state.get("cache_store")
    cache_key = f"public:site-lottery:v1:id:{site_id}"
    if cache is not None:
        try:
            cached = cache.get(cache_key)
            lottery_type = _parse_cached_lottery_type(cached)
        except CacheUnavailable:
            lottery_type = None
        if lottery_type is not None:
            return lottery_type

    site_ctx = resolve_site_context(ctx.write_db_path, path_site_id=site_id, query=ctx.query)
    lottery_type = int(site_ctx.lottery_type_id or 1)
    if cache is not None:
        try:
            cache.set(cache_key, str(lottery_type).encode("ascii"), ttl_seconds=60)
        except CacheUnavailable:
            pass
    return lottery_type


def _parse_cached_lottery_type(value: object) -> int | None:
    if not isinstance(value, bytes):
        return None
    try:
        decoded = value.decode("ascii")
        lottery_type = int(decoded)
    except (UnicodeDecodeError, ValueError):
        return None
    return lottery_type if lottery_type > 0 else None


def _backfill_latest_draw(
    snapshots: Any | None,
    lottery_type: int,
    payload: dict,
) -> None:
    if snapshots is None:
        return
    version = str(payload.get("current_issue") or "")
    if not version:
        return
    try:
        snapshots.publish_latest_draw(lottery_type, payload, version=version, is_opened=True)
    except (CacheUnavailable, ValueError):
        # Cache safety and availability never change the authoritative response.
        return


def _backfill_current_period(
    snapshots: Any | None,
    lottery_type: int,
    payload: dict,
) -> None:
    if snapshots is None:
        return
    version = str(payload.get("current_period") or "")
    if not version:
        return
    try:
        snapshots.publish_current_period(lottery_type, payload, version=version, is_opened=True)
    except (CacheUnavailable, ValueError):
        # Cache safety and availability never change the authoritative response.
        return


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


def site_links(ctx: RequestContext) -> None:
    """公开站点链接接口。

    根据 current_site_key 排除当前站点，返回已启用且有域名的外部站点链接。
    不需要管理员鉴权。
    """
    current_site_key = str(ctx.query_value("current_site_key", "") or "").strip()
    ctx.send_json(get_public_site_links(ctx.db_path, current_site_key))


def traffic_events(ctx: RequestContext) -> None:
    ctx.send_json(
        record_traffic_event(
            ctx.db_path,
            ctx.body,
            ip_address=_client_ip(ctx),
            user_agent=str(ctx.headers.get("User-Agent", "") or ""),
        )
    )
