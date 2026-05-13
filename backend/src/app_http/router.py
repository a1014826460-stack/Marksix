from __future__ import annotations

import logging
import os
import re
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Pattern

from http import HTTPStatus

from core.errors import AppError, UnauthorizedError, ForbiddenError, NotFoundError
from .auth import get_current_user
from .request_context import RequestContext

_DEBUG = os.environ.get("LOTTERY_DEBUG", "").strip() in ("1", "true", "yes", "on")


RouteHandler = Callable[[RequestContext], None]
RouteGuard = Callable[[RequestContext], Any]


@dataclass(frozen=True)
class Route:
    method: str | None
    matcher: Callable[[RequestContext], bool]
    handler: RouteHandler
    guard: RouteGuard | None = None


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _query_snapshot(ctx: RequestContext) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for key, values in ctx.query.items():
        if not values:
            snapshot[key] = ""
        elif len(values) == 1:
            snapshot[key] = values[0]
        else:
            snapshot[key] = values
    return snapshot


def _build_request_log_extra(ctx: RequestContext) -> dict[str, Any]:
    current_user = get_current_user(ctx) or {}
    cached_body = getattr(ctx, "_body", None)
    req_params: dict[str, Any] = {
        "path": ctx.path,
        "raw_path": ctx.raw_path,
        "query": _query_snapshot(ctx),
    }
    if cached_body is not None:
        req_params["body"] = cached_body

    query_or_body = cached_body if isinstance(cached_body, dict) else {}
    site_id = _as_int((query_or_body.get("site_id") if isinstance(query_or_body, dict) else None) or ctx.query_value("site_id"))
    web_id = _as_int(
        (query_or_body.get("web_id") if isinstance(query_or_body, dict) else None)
        or (query_or_body.get("web") if isinstance(query_or_body, dict) else None)
        or ctx.query_value("web_id")
        or ctx.query_value("web")
    )
    lottery_type_id = _as_int(
        (query_or_body.get("lottery_type_id") if isinstance(query_or_body, dict) else None)
        or (query_or_body.get("lottery_type") if isinstance(query_or_body, dict) else None)
        or (query_or_body.get("type") if isinstance(query_or_body, dict) else None)
        or ctx.query_value("lottery_type_id")
        or ctx.query_value("lottery_type")
        or ctx.query_value("type")
    )
    year = _as_int(
        (query_or_body.get("year") if isinstance(query_or_body, dict) else None)
        or ctx.query_value("year")
    )
    term = _as_int(
        (query_or_body.get("term") if isinstance(query_or_body, dict) else None)
        or ctx.query_value("term")
        or ctx.query_value("issue")
    )

    return {
        "user_id": current_user.get("id", ""),
        "request_path": ctx.path,
        "request_method": ctx.method,
        "req_params": req_params,
        "site_id": site_id,
        "web_id": web_id,
        "lottery_type_id": lottery_type_id,
        "year": year,
        "term": term,
    }


class Router:
    def __init__(self) -> None:
        self._routes: list[Route] = []

    def add(
        self,
        method: str | None,
        path: str,
        handler: RouteHandler,
        *,
        guard: RouteGuard | None = None,
    ) -> None:
        self._routes.append(
            Route(
                method=method,
                matcher=lambda ctx, exact_path=path: ctx.path == exact_path,
                handler=handler,
                guard=guard,
            )
        )

    def add_prefix(
        self,
        method: str | None,
        prefix: str,
        handler: RouteHandler,
        *,
        guard: RouteGuard | None = None,
    ) -> None:
        self._routes.append(
            Route(
                method=method,
                matcher=lambda ctx, path_prefix=prefix: ctx.path.startswith(path_prefix),
                handler=handler,
                guard=guard,
            )
        )

    def add_regex(
        self,
        method: str | None,
        pattern: str | Pattern[str],
        handler: RouteHandler,
        *,
        guard: RouteGuard | None = None,
    ) -> None:
        compiled = re.compile(pattern) if isinstance(pattern, str) else pattern
        self._routes.append(
            Route(
                method=method,
                matcher=lambda ctx, regex=compiled: bool(regex.match(ctx.path)),
                handler=handler,
                guard=guard,
            )
        )

    def dispatch(self, ctx: RequestContext) -> None:
        try:
            for route in self._routes:
                if route.method is not None and route.method != ctx.method:
                    continue
                if not route.matcher(ctx):
                    continue
                if route.guard is not None:
                    route.guard(ctx)
                route.handler(ctx)
                return
            ctx.send_error_json(HTTPStatus.NOT_FOUND, "接口不存在")
        except Exception as exc:
            logger = logging.getLogger("app.request")
            logger.exception(
                "Request failed: %s %s -> %s",
                ctx.command,
                ctx.raw_path,
                exc,
                extra=_build_request_log_extra(ctx),
            )
            if isinstance(exc, AppError):
                status = HTTPStatus(exc.status_code)
                payload: dict[str, Any] = {"ok": False, "error": str(exc), "code": exc.code}
                if _DEBUG:
                    payload["detail"] = traceback.format_exc()
                ctx.response.send_json(payload, status)
            elif isinstance(exc, KeyError):
                ctx.send_error_json(HTTPStatus.NOT_FOUND, str(exc))
            elif isinstance(exc, PermissionError):
                ctx.send_error_json(HTTPStatus.FORBIDDEN, str(exc))
            elif isinstance(exc, ValueError):
                ctx.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
            else:
                payload = {"ok": False, "error": "服务器内部错误"}
                if _DEBUG:
                    payload["detail"] = traceback.format_exc()
                ctx.response.send_json(payload, HTTPStatus.INTERNAL_SERVER_ERROR)
