from __future__ import annotations

from http import HTTPStatus

from admin.crud import create_number, delete_number, list_numbers, update_number

from http.request_context import RequestContext
from http.router import Router


def register(router: Router) -> None:
    router.add("GET", "/api/admin/numbers", list_number_routes)
    router.add("POST", "/api/admin/numbers", create_number_route)
    router.add_prefix(None, "/api/admin/numbers/", number_detail)


def list_number_routes(ctx: RequestContext) -> None:
    limit = int(ctx.query_value("limit", "300") or 300)
    keyword = ctx.query_value("keyword", "") or ""
    ctx.send_json({"numbers": list_numbers(ctx.db_path, limit, keyword)})


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
