from __future__ import annotations

import html
import json
import mimetypes
from pathlib import Path
from typing import Any

from http import HTTPStatus


class ResponseWriter:
    def __init__(self, handler: Any):
        self._handler = handler

    def send_cors_headers(self) -> None:
        self._handler.send_header("Access-Control-Allow-Origin", "*")
        self._handler.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self._handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def send_json(self, data: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self._handler.send_response(status)
        self.send_cors_headers()
        self._handler.send_header("Content-Type", "application/json; charset=utf-8")
        self._handler.send_header("Content-Length", str(len(body)))
        self._handler.end_headers()
        self._handler.wfile.write(body)

    def send_html(self, text: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = text.encode("utf-8")
        self._handler.send_response(status)
        self._handler.send_header("Content-Type", "text/html; charset=utf-8")
        self._handler.send_header("Content-Length", str(len(body)))
        self._handler.end_headers()
        self._handler.wfile.write(body)

    def send_error_json(
        self,
        status: HTTPStatus,
        message: str,
        detail: str | None = None,
    ) -> None:
        payload = {"ok": False, "error": message}
        if detail:
            payload["detail"] = detail
        self.send_json(payload, status)

    def serve_upload(self, path: str, base_dir: Path) -> None:
        filename = Path(path).name
        if not filename:
            self.send_error_json(HTTPStatus.NOT_FOUND, "文件不存在")
            return
        file_path = base_dir / filename
        resolved = file_path.resolve()
        if not resolved.is_file() or not resolved.is_relative_to(base_dir.resolve()):
            self.send_error_json(HTTPStatus.NOT_FOUND, "文件不存在")
            return
        mime_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        try:
            data = resolved.read_bytes()
        except OSError:
            self.send_error_json(HTTPStatus.NOT_FOUND, "文件不存在")
            return
        self._handler.send_response(HTTPStatus.OK)
        self._handler.send_header("Content-Type", mime_type)
        self._handler.send_header("Content-Length", str(len(data)))
        self._handler.send_header("Cache-Control", "public, max-age=86400")
        self._handler.end_headers()
        self._handler.wfile.write(data)

    def redirect(self, location: str) -> None:
        self._handler.send_response(HTTPStatus.FOUND)
        self._handler.send_header("Location", html.escape(location, quote=True))
        self._handler.end_headers()
