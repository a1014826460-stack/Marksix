from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .response import ResponseWriter


class RequestContext:
    """HTTP 请求上下文，封装一次请求的全部信息。

    Attributes:
        method: HTTP 方法（GET/POST/PUT/DELETE 等）
        path: 归一化后的请求路径（去掉尾部斜杠）
        query: 解析后的查询参数字典
        body: 缓存的 JSON 请求体（首次访问时解析）
        db_path: 当前数据库路径
        user: 当前登录用户信息（通过鉴权中间件设置）
        request_id: 请求唯一标识
        handler: 原始 HTTP handler 引用
    """

    def __init__(self, handler: Any, method: str):
        self.handler = handler
        self.method = method
        self.raw_path = handler.path
        self.parsed_url = urlparse(handler.path)
        self.path = self.parsed_url.path.rstrip("/") or "/"
        self.query = parse_qs(self.parsed_url.query)
        self.response = ResponseWriter(handler)
        self.state: dict[str, Any] = {}
        self._body: dict[str, Any] | None = None
        self.request_id: str = uuid.uuid4().hex[:12]

    @property
    def body(self) -> dict[str, Any]:
        """缓存的 JSON 请求体，首次访问时解析并缓存。"""
        if self._body is None:
            self._body = self.read_json()
        return self._body

    @property
    def user(self) -> dict[str, Any] | None:
        """当前登录用户信息（由鉴权中间件设置）。"""
        return self.state.get("current_user")

    @property
    def db_path(self) -> str | Path:
        return self.handler.server.db_path  # type: ignore[attr-defined]

    @property
    def headers(self) -> Any:
        return self.handler.headers

    @property
    def command(self) -> str:
        return self.handler.command

    def query_value(self, name: str, default: str | None = None) -> str | None:
        return self.query.get(name, [default])[0]

    def bearer_token(self) -> str | None:
        header = self.headers.get("Authorization", "")
        if header.lower().startswith("bearer "):
            return header.split(" ", 1)[1].strip()
        return None

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        raw = self.handler.rfile.read(length).decode("utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("JSON body 必须是对象")
        return data

    def send_json(self, data: Any, status: Any = None) -> None:
        if status is None:
            self.response.send_json(data)
            return
        self.response.send_json(data, status)

    def send_html(self, text: str, status: Any = None) -> None:
        if status is None:
            self.response.send_html(text)
            return
        self.response.send_html(text, status)

    def send_error_json(self, status: Any, message: str, detail: str | None = None) -> None:
        self.response.send_error_json(status, message, detail)

    def serve_upload(self, path: str, base_dir: Path) -> None:
        self.response.serve_upload(path, base_dir)

    def redirect(self, location: str) -> None:
        self.response.redirect(location)
