from __future__ import annotations

import io
import json
from typing import Any

from app_http.request_context import RequestContext


class Headers(dict):
    def get(self, key: str, default: Any = None) -> Any:
        return super().get(key, default)


class StubServer:
    db_path = "postgresql://test:test@localhost:5432/test"


class StubHandler:
    def __init__(self, path: str, method: str = "GET", body: bytes = b""):
        self.path = path
        self.command = method
        self.headers = Headers({"Content-Length": str(len(body))} if body else {})
        self.server = StubServer()
        self.rfile = io.BytesIO(body)
        self.response_status = None
        self.response_headers: list[tuple[str, str]] = []
        self._body = bytearray()
        self.client_address = ("127.0.0.1", 12345)

    @property
    def wfile(self):
        return self

    def write(self, data: bytes) -> None:
        self._body.extend(data)

    def send_response(self, status: Any) -> None:
        self.response_status = status

    def send_header(self, key: str, value: str) -> None:
        self.response_headers.append((key, value))

    def end_headers(self) -> None:
        return None


def make_ctx(path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> RequestContext:
    raw = json.dumps(payload or {}).encode("utf-8") if payload is not None else b""
    return RequestContext(StubHandler(path, method, raw), method)


def response_json(ctx: RequestContext) -> dict[str, Any]:
    return json.loads(bytes(ctx.handler._body).decode("utf-8"))
