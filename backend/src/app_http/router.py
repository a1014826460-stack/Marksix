from __future__ import annotations

import logging
import re
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Pattern

from http import HTTPStatus

from core.errors import AppError, UnauthorizedError, ForbiddenError, NotFoundError
from .auth import get_current_user
from .request_context import RequestContext


RouteHandler = Callable[[RequestContext], None]
RouteGuard = Callable[[RequestContext], Any]


@dataclass(frozen=True)
class Route:
    method: str | None
    matcher: Callable[[RequestContext], bool]
    handler: RouteHandler
    guard: RouteGuard | None = None


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
                extra={
                    "user_id": (get_current_user(ctx) or {}).get("id", ""),
                },
            )
            if isinstance(exc, AppError):
                status = HTTPStatus(exc.status_code)
            elif isinstance(exc, KeyError):
                status = HTTPStatus.NOT_FOUND
            elif isinstance(exc, PermissionError):
                status = HTTPStatus.FORBIDDEN
            else:
                status = HTTPStatus.BAD_REQUEST
            ctx.send_error_json(status, str(exc), traceback.format_exc())
