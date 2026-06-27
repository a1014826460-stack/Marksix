from __future__ import annotations

import json
from unittest.mock import patch

from app_http.request_context import RequestContext
from routes import public_routes


class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class _StubServer:
    db_path = "postgresql://test:test@localhost:5432/test"


class _StubHandler:
    def __init__(self, path: str):
        self.path = path
        self.command = "GET"
        self.headers = _Headers({})
        self.server = _StubServer()
        self.response_status = None
        self.response_headers: list[tuple[str, str]] = []
        self._body = bytearray()

    @property
    def wfile(self):
        return self

    def write(self, data: bytes):
        self._body.extend(data)

    def send_response(self, status):
        self.response_status = status

    def send_header(self, key, value):
        self.response_headers.append((key, value))

    def end_headers(self):
        return None


def _make_ctx(path: str) -> RequestContext:
    return RequestContext(_StubHandler(path), "GET")


def _response_json(ctx: RequestContext) -> dict:
    return json.loads(bytes(ctx.handler._body).decode("utf-8"))


def test_public_latest_draw_contract():
    ctx = _make_ctx("/api/public/latest-draw?lottery_type=3")
    payload = {
        "year": 2026,
        "term": 188,
        "numbers": "01,02,03,04,05,06,07",
        "is_opened": True,
    }

    with patch("routes.public_routes.get_public_latest_draw", return_value=payload) as latest_draw:
        public_routes.latest_draw(ctx)

    latest_draw.assert_called_once_with(ctx.db_path, 3)
    assert ctx.handler.response_status == 200
    assert _response_json(ctx) == payload


def test_public_next_draw_deadline_contract_adds_server_time():
    ctx = _make_ctx("/api/public/next-draw-deadline?lottery_type=2")
    payload = {
        "draw_deadline": "1782570600000",
        "next_time": "2026-06-27 21:30:00",
    }

    with patch("routes.public_routes.time.time", return_value=1782560000), \
         patch("routes.public_routes.get_public_next_draw_deadline", return_value=dict(payload)) as deadline:
        public_routes.next_draw_deadline(ctx)

    deadline.assert_called_once_with(ctx.db_path, 2)
    assert ctx.handler.response_status == 200
    assert _response_json(ctx) == {
        "draw_deadline": "1782570600000",
        "next_time": "2026-06-27 21:30:00",
        "server_time": "1782560000",
    }
