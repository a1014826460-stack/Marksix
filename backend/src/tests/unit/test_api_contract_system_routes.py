from __future__ import annotations

import json
from unittest.mock import MagicMock

from app_http.request_context import RequestContext
from routes import system_routes


def _make_handler(path: str, method: str = "GET"):
    handler = MagicMock()
    handler.path = path
    handler.command = method
    handler.headers = {}
    handler.server.db_path = "postgresql://test:test@localhost:5432/test"
    handler.wfile = MagicMock()
    return handler


def _make_ctx(path: str, method: str = "GET") -> RequestContext:
    handler = _make_handler(path, method)
    ctx = RequestContext(handler, method)
    ctx.path = path.rstrip("/") or "/"
    ctx.state["detect_database_engine"] = lambda db_path: "postgres"
    ctx.state["database_summary"] = lambda db_path: {"tables": 12, "engine": "postgres"}
    return ctx


def _response_json(ctx: RequestContext) -> dict:
    call_args = ctx.handler.wfile.write.call_args
    assert call_args is not None
    body = call_args[0][0].decode("utf-8")
    return json.loads(body)


def test_health_route_contract():
    ctx = _make_ctx("/health")

    system_routes.health(ctx)

    assert ctx.handler.send_response.call_args[0][0] == 200
    assert _response_json(ctx) == {"status": "ok", "engine": "postgres"}


def test_api_health_route_contract():
    ctx = _make_ctx("/api/health")

    system_routes.api_health(ctx)

    payload = _response_json(ctx)
    assert ctx.handler.send_response.call_args[0][0] == 200
    assert payload["ok"] is True
    assert payload["summary"] == {"tables": 12, "engine": "postgres"}
