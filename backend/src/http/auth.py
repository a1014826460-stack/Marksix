"""HTTP 层鉴权：从请求中提取用户、校验权限。

所有鉴权函数均接受 RequestContext，
由 routes 层在处理请求前调用。
"""

from __future__ import annotations

from typing import Any

from auth import auth_user_from_token, ensure_generation_permission
from core.errors import UnauthorizedError, ForbiddenError

from .request_context import RequestContext


def get_current_user(ctx: RequestContext) -> dict[str, Any] | None:
    """从请求中提取当前登录用户，结果缓存在 ctx.state 中。"""
    if "current_user" not in ctx.state:
        ctx.state["current_user"] = auth_user_from_token(ctx.db_path, ctx.bearer_token())
    return ctx.state["current_user"]


def require_authenticated(ctx: RequestContext) -> dict[str, Any]:
    """要求请求已认证，否则抛出 UnauthorizedError。"""
    user = get_current_user(ctx)
    if not user:
        raise UnauthorizedError("未登录或登录已失效")
    return user


def require_admin(ctx: RequestContext) -> dict[str, Any]:
    """要求当前用户具有管理员权限（super_admin 或 admin）。

    目前 admin 及以上角色拥有全部管理权限，
    后续可细化角色判断。
    """
    user = require_authenticated(ctx)
    role = str(user.get("role") or "").strip().lower()
    if role not in ("super_admin", "admin"):
        raise ForbiddenError("需要管理员权限")
    return user


def require_generation_access(ctx: RequestContext) -> dict[str, Any]:
    """要求当前用户具有预测资料生成权限。"""
    user = get_current_user(ctx)
    ensure_generation_permission(user)
    return user or {}
