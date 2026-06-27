from __future__ import annotations

import io
import json
from unittest.mock import patch

from app_http.request_context import RequestContext
from routes import auth_routes


class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class _StubServer:
    db_path = "postgresql://test:test@localhost:5432/test"


class _StubHandler:
    def __init__(self, path: str, method: str = "POST", body: bytes = b""):
        self.path = path
        self.command = method
        self.headers = _Headers({"Content-Length": str(len(body))})
        self.server = _StubServer()
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.client_address = ("127.0.0.1", 12345)
        self.response_status = None
        self.response_headers: list[tuple[str, str]] = []

    def send_response(self, status):
        self.response_status = status

    def send_header(self, key, value):
        self.response_headers.append((key, value))

    def end_headers(self):
        return None


def _make_ctx(path: str, method: str = "POST", payload: dict | None = None) -> RequestContext:
    raw = json.dumps(payload or {}).encode("utf-8")
    handler = _StubHandler(path, method, raw)
    ctx = RequestContext(handler, method)
    ctx.path = path.rstrip("/") or "/"
    return ctx


def _response_json(ctx: RequestContext) -> dict:
    return json.loads(ctx.handler.wfile.getvalue().decode("utf-8"))


def test_captcha_route_contract():
    ctx = _make_ctx("/api/auth/captcha", method="GET")

    with patch("routes.auth_routes.generate_captcha", return_value=("1234", "data:image/svg+xml;base64,abc")), \
         patch("routes.auth_routes.store_captcha") as store_mock:
        auth_routes.captcha(ctx)

    payload = _response_json(ctx)
    assert ctx.handler.response_status == 200
    assert payload == {
        "image": "data:image/svg+xml;base64,abc",
        "expires_in_seconds": 300,
    }
    assert store_mock.called


def test_login_missing_captcha_contract():
    ctx = _make_ctx("/api/auth/login", payload={"username": "admin", "password": "secret"})

    with patch("routes.auth_routes.check_login_locked", return_value=(False, "")):
        auth_routes.login(ctx)

    payload = _response_json(ctx)
    assert ctx.handler.response_status == 400
    assert payload == {"ok": False, "error": "请输入验证码"}


def test_login_invalid_captcha_contract():
    ctx = _make_ctx(
        "/api/auth/login",
        payload={"username": "admin", "password": "secret", "captcha": "0000"},
    )

    with patch("routes.auth_routes.check_login_locked", return_value=(False, "")), \
         patch("routes.auth_routes.verify_captcha", return_value=False), \
         patch(
             "routes.auth_routes.record_login_failure",
             return_value={
                 "attempt_count": 1,
                 "max_attempts": 5,
                 "locked": False,
                 "locked_minutes": 0,
             },
         ):
        auth_routes.login(ctx)

    payload = _response_json(ctx)
    assert ctx.handler.response_status == 400
    assert payload == {"ok": False, "error": "验证码错误"}
