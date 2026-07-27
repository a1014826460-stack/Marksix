from __future__ import annotations

from http import HTTPStatus

from admin.crud import delete_draw, list_draws, save_draw
from domains.lottery.service import (
    autofill_taiwan_future_draws,
    get_latest_opened_draw_term,
    get_taiwan_future_autofill_settings,
    save_taiwan_future_autofill_settings,
)
from domains.scheduler.service import get_taiwan_future_autofill_schedule_status

from app_http.request_context import RequestContext
from app_http.router import Router
from app_http.security import MAX_ADMIN_LIST_LIMIT, parse_bounded_int
from app_http.auth import require_admin


def register(router: Router) -> None:
    router.add("GET", "/api/admin/draws", list_draw_routes, guard=require_admin)
    router.add("POST", "/api/admin/draws", create_draw, guard=require_admin)
    router.add(
        "POST",
        "/api/admin/draws/auto-fill-future",
        autofill_future_draws,
        guard=require_admin,
    )
    router.add(
        "GET",
        "/api/admin/draws/auto-fill-future/settings",
        get_autofill_future_settings,
        guard=require_admin,
    )
    router.add(
        "PUT",
        "/api/admin/draws/auto-fill-future/settings",
        save_autofill_future_settings,
        guard=require_admin,
    )
    router.add_regex(None, r"^/api/admin/draws/\d+$", draw_detail, guard=require_admin)
    router.add("GET", "/api/admin/lottery-draws/latest-term", latest_term, guard=require_admin)


def list_draw_routes(ctx: RequestContext) -> None:
    limit = parse_bounded_int(
        ctx.query_value("limit", ctx.query_value("page_size", "20")),
        default=20,
        maximum=MAX_ADMIN_LIST_LIMIT,
        field_name="limit",
    )
    page = parse_bounded_int(
        ctx.query_value("page", "1"),
        default=1,
        maximum=MAX_ADMIN_LIST_LIMIT,
        field_name="page",
    )
    offset = (page - 1) * limit
    lottery_type_id_raw = ctx.query_value("lottery_type_id", None)
    lottery_type_id = int(lottery_type_id_raw) if lottery_type_id_raw else None
    ctx.send_json(list_draws(ctx.db_path, limit=limit, offset=offset, lottery_type_id=lottery_type_id))


def create_draw(ctx: RequestContext) -> None:
    ctx.send_json({"draw": save_draw(ctx.db_path, ctx.read_json())}, HTTPStatus.CREATED)


def _parse_autofill_count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 60:
        raise ValueError("自动填写期数必须在 1 到 60 之间")
    return value


def autofill_future_draws(ctx: RequestContext) -> None:
    payload = ctx.read_json()
    count = _parse_autofill_count(payload.get("count", 12))
    result = autofill_taiwan_future_draws(ctx.db_path, count=count)
    ctx.send_json({"ok": True, "data": result}, HTTPStatus.CREATED)


def get_autofill_future_settings(ctx: RequestContext) -> None:
    settings = get_taiwan_future_autofill_settings(ctx.db_path)
    status = get_taiwan_future_autofill_schedule_status(ctx.db_path)
    ctx.send_json({"ok": True, "data": settings | status})


def save_autofill_future_settings(ctx: RequestContext) -> None:
    user = ctx.state.get("current_user") or {}
    settings = save_taiwan_future_autofill_settings(
        ctx.db_path,
        ctx.read_json(),
        changed_by=str(user.get("username") or "unknown"),
    )
    ctx.send_json({"ok": True, "data": settings})


def draw_detail(ctx: RequestContext) -> None:
    draw_id = int(ctx.path.split("/")[-1])
    if ctx.method in {"PUT", "PATCH"}:
        ctx.send_json({"draw": save_draw(ctx.db_path, ctx.read_json(), draw_id)})
        return
    if ctx.method == "DELETE":
        delete_draw(ctx.db_path, draw_id)
        ctx.send_json({"ok": True})
        return
    raise KeyError("接口不存在")


def latest_term(ctx: RequestContext) -> None:
    lt_id = int(ctx.query_value("lottery_type_id", "1") or 1)
    ctx.send_json(get_latest_opened_draw_term(ctx.db_path, lt_id))
