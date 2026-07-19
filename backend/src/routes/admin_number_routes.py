from __future__ import annotations

from http import HTTPStatus

from admin.crud import create_number, delete_number, list_numbers, update_number

from app_http.request_context import RequestContext
from app_http.router import Router
from app_http.security import MAX_ADMIN_LIST_LIMIT, parse_bounded_int
from app_http.auth import require_admin


def register(router: Router) -> None:
    router.add("GET", "/api/admin/numbers", list_number_routes, guard=require_admin)
    router.add("POST", "/api/admin/numbers", create_number_route, guard=require_admin)
    router.add_prefix(None, "/api/admin/numbers/", number_detail, guard=require_admin)


def list_number_routes(ctx: RequestContext) -> None:
    limit = parse_bounded_int(
        ctx.query_value("limit", "300"),
        default=300,
        maximum=MAX_ADMIN_LIST_LIMIT,
        field_name="limit",
    )
    keyword = ctx.query_value("keyword", "") or ""
    sign = ctx.query_value("sign", "") or ""
    ctx.send_json({"numbers": list_numbers(ctx.db_path, limit, keyword, sign)})


def create_number_route(ctx: RequestContext) -> None:
    ctx.send_json({"number": create_number(ctx.db_path, ctx.read_json())}, HTTPStatus.CREATED)


def number_detail(ctx: RequestContext) -> None:
    number_id = int(ctx.path.split("/")[-1])
    if ctx.method in {"PUT", "PATCH"}:
        ctx.send_json({"number": update_number(ctx.db_path, number_id, ctx.read_json())})
        return
    if ctx.method == "DELETE":
        delete_number(ctx.db_path, number_id)
        ctx.send_json({"ok": True})
        return
    raise KeyError("接口不存在")
