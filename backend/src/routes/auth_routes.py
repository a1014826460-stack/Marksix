from __future__ import annotations

from auth import login_user, logout_user
from http.auth import require_authenticated
from http.request_context import RequestContext
from http.router import Router


def register(router: Router) -> None:
    router.add("POST", "/api/auth/login", login)
    router.add("GET", "/api/auth/me", me)
    router.add("POST", "/api/auth/logout", logout)


def login(ctx: RequestContext) -> None:
    body = ctx.read_json()
    ctx.send_json(
        login_user(
            ctx.db_path,
            str(body.get("username") or ""),
            str(body.get("password") or ""),
        )
    )


def me(ctx: RequestContext) -> None:
    user = require_authenticated(ctx)
    ctx.send_json({"user": user})


def logout(ctx: RequestContext) -> None:
    logout_user(ctx.db_path, ctx.bearer_token())
    ctx.send_json({"ok": True})
