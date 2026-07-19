from __future__ import annotations

from http import HTTPStatus

from admin.crud import delete_draw, list_draws, save_draw
from domains.lottery.service import get_latest_opened_draw_term

from app_http.request_context import RequestContext
from app_http.router import Router
from app_http.security import MAX_ADMIN_LIST_LIMIT, parse_bounded_int
from app_http.auth import require_admin


def register(router: Router) -> None:
    router.add("GET", "/api/admin/draws", list_draw_routes, guard=require_admin)
    router.add("POST", "/api/admin/draws", create_draw, guard=require_admin)
    router.add_prefix(None, "/api/admin/draws/", draw_detail, guard=require_admin)
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
