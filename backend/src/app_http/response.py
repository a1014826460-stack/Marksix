from __future__ import annotations

import html
import json
import mimetypes
from pathlib import Path
from typing import Any

from http import HTTPStatus

from .security import cors_allowed_origin


class ResponseWriter:
    def __init__(self, handler: Any):
        self._handler = handler
        self._pending_headers: list[tuple[str, str]] = []

    def _send_pending_headers(self) -> None:
        for key, value in self._pending_headers:
            self._handler.send_header(key, value)
        self._pending_headers.clear()

    def send_cors_headers(self) -> None:
        headers = getattr(self._handler, "headers", None)
        origin = headers.get("Origin") if hasattr(headers, "get") else None
        allowed_origin = cors_allowed_origin(origin)
        if not allowed_origin:
            return
        self._handler.send_header("Access-Control-Allow-Origin", allowed_origin)
        self._handler.send_header("Vary", "Origin")
        self._handler.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self._handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def send_json(self, data: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self._handler.send_response(status)
        self.send_cors_headers()
        self._send_pending_headers()
        self._handler.send_header("Content-Type", "application/json; charset=utf-8")
        self._handler.send_header("Content-Length", str(len(body)))
        self._handler.end_headers()
        self._handler.wfile.write(body)

    def set_session_cookie(self, token: str, *, max_age_seconds: int, secure: bool) -> None:
        attributes = [
            f"liuhecai_admin_session={token}",
            "Path=/",
            f"Max-Age={max(0, int(max_age_seconds))}",
            "HttpOnly",
            "SameSite=Strict",
        ]
        if secure:
            attributes.append("Secure")
        self._pending_headers.append(("Set-Cookie", "; ".join(attributes)))

    def clear_session_cookie(self, *, secure: bool) -> None:
        self.set_session_cookie("", max_age_seconds=0, secure=secure)


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
        normalized_path = str(path or "").strip()
        upload_prefix = "/uploads/"
        if not normalized_path.startswith(upload_prefix):
            self.send_error_json(HTTPStatus.NOT_FOUND, "File not found")
            return

        relative_path = normalized_path[len(upload_prefix):].lstrip("/")
        if not relative_path:
            self.send_error_json(HTTPStatus.NOT_FOUND, "File not found")
            return

        base_dir_resolved = base_dir.resolve()
        candidate_paths = [base_dir / Path(relative_path)]
        flat_filename = Path(relative_path).name
        if flat_filename and flat_filename != relative_path:
            candidate_paths.append(base_dir / flat_filename)

        resolved = None
        for file_path in candidate_paths:
            candidate = file_path.resolve()
            if candidate.is_file() and candidate.is_relative_to(base_dir_resolved):
                resolved = candidate
                break

        if resolved is None:
            self.send_error_json(HTTPStatus.NOT_FOUND, "File not found")
            return

        mime_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        try:
            data = resolved.read_bytes()
        except OSError:
            self.send_error_json(HTTPStatus.NOT_FOUND, "File not found")
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
