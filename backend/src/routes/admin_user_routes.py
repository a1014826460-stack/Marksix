from __future__ import annotations

from http import HTTPStatus

from admin.crud import delete_user, list_users, save_user

from http.request_context import RequestContext
from http.router import Router


def register(router: Router) -> None:
    router.add("GET", "/api/admin/users", list_user_routes)
    router.add("POST", "/api/admin/users", create_user)
    router.add_prefix(None, "/api/admin/users/", user_detail)


def list_user_routes(ctx: RequestContext) -> None:
    ctx.send_json({"users": list_users(ctx.db_path)})


def create_user(ctx: RequestContext) -> None:
    ctx.send_json({"user": save_user(ctx.db_path, ctx.read_json())}, HTTPStatus.CREATED)


def user_detail(ctx: RequestContext) -> None:
    user_id = int(ctx.path.split("/")[-1])
    if ctx.method in {"PUT", "PATCH"}:
        ctx.send_json({"user": save_user(ctx.db_path, ctx.read_json(), user_id)})
        return
    if ctx.method == "DELETE":
        delete_user(ctx.db_path, user_id)
        ctx.send_json({"ok": True})
        return
    raise KeyError("接口不存在")
