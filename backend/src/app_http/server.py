"""HTTP 服务核心：build_router、ApiHandler、run_server、build_parser。

这是整个后台系统唯一的服务实现副本。main.py 和 app.py 都从此模块导入。
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import Any

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from core.errors import AppError, UnauthorizedError, ForbiddenError
from crawler.crawler_service import CrawlerScheduler
from db import DEFAULT_POSTGRES_DSN, detect_database_engine, is_postgres_target
from logger import init_logging
from predict.mechanisms import ensure_prediction_configs_loaded
from runtime_config import get_bootstrap_config_value
from tables import database_summary, ensure_admin_tables

from .auth import get_current_user, require_authenticated
from .request_context import RequestContext
from .router import Router

from routes import (
    admin_alert_routes,
    admin_backfill_routes,
    admin_config_routes,
    admin_crawler_routes,
    admin_draw_routes,
    admin_log_routes,
    admin_lottery_routes,
    admin_lottery_routes_extra,
    admin_number_routes,
    admin_payload_routes,
    admin_prediction_routes,
    admin_site_routes,
    admin_user_routes,
    auth_routes,
    job_routes,
    legacy_routes,
    public_routes,
    system_routes,
)

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
LEGACY_IMAGES_DIR = _BACKEND_ROOT / str(get_bootstrap_config_value("legacy.images_dir", "data/Images"))
LEGACY_POST_LIST_PC = int(get_bootstrap_config_value("legacy.post_list_pc", 305))
LEGACY_POST_LIST_WEB = int(get_bootstrap_config_value("legacy.post_list_web", 4))
LEGACY_POST_LIST_TYPE = int(get_bootstrap_config_value("legacy.post_list_type", 3))

ADMIN_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Liuhecai Backend</title>
</head>
<body>
  <main style="font-family: sans-serif; max-width: 720px; margin: 48px auto; line-height: 1.6;">
    <h1>Liuhecai Backend API</h1>
    <p>Python backend service is running.</p>
    <p>Use the Next.js admin app for management workflows.</p>
  </main>
</body>
</html>
"""


def build_router() -> Router:
    router = Router()
    system_routes.register(router, admin_html=ADMIN_HTML, legacy_images_dir=LEGACY_IMAGES_DIR)
    auth_routes.register(router)
    public_routes.register(router)
    legacy_routes.register(
        router,
        default_pc=LEGACY_POST_LIST_PC,
        default_web=LEGACY_POST_LIST_WEB,
        default_type=LEGACY_POST_LIST_TYPE,
    )
    admin_user_routes.register(router)
    admin_config_routes.register(router)
    admin_prediction_routes.register(router)
    admin_lottery_routes.register(router)
    admin_draw_routes.register(router)
    admin_crawler_routes.register(router)
    admin_number_routes.register(router)
    admin_site_routes.register(router)
    admin_payload_routes.register(router)
    admin_lottery_routes_extra.register(
        router,
        default_pc=LEGACY_POST_LIST_PC,
        default_web=LEGACY_POST_LIST_WEB,
        default_type=LEGACY_POST_LIST_TYPE,
    )
    admin_log_routes.register(router)
    admin_alert_routes.register(router)
    admin_backfill_routes.register(router)
    job_routes.register(router)
    return router


ROUTER = build_router()

_DEBUG = os.environ.get("LOTTERY_DEBUG", "").strip() in ("1", "true", "yes", "on")


def _dispatch_error_response(ctx: RequestContext, exc: Exception, logger: logging.Logger) -> None:
    """统一错误响应：根据异常类型和调试模式构建响应。"""
    if isinstance(exc, UnauthorizedError):
        ctx.send_error_json(HTTPStatus.UNAUTHORIZED, str(exc))
    elif isinstance(exc, ForbiddenError):
        ctx.send_error_json(HTTPStatus.FORBIDDEN, str(exc))
    elif isinstance(exc, AppError):
        status = HTTPStatus(exc.status_code)
        payload = {"ok": False, "error": str(exc), "code": exc.code}
        if _DEBUG:
            import traceback
            payload["detail"] = traceback.format_exc()
        ctx.response.send_json(payload, status)
    elif isinstance(exc, KeyError):
        ctx.send_error_json(HTTPStatus.NOT_FOUND, str(exc))
    elif isinstance(exc, PermissionError):
        ctx.send_error_json(HTTPStatus.FORBIDDEN, str(exc))
    elif isinstance(exc, ValueError):
        ctx.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
    else:
        logger.exception("Unhandled error: %s %s", ctx.command, ctx.raw_path)
        payload = {"ok": False, "error": "服务器内部错误"}
        if _DEBUG:
            import traceback
            payload["detail"] = traceback.format_exc()
        ctx.response.send_json(payload, HTTPStatus.INTERNAL_SERVER_ERROR)


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "LiuhecaiBackend/1.0"

    @property
    def db_path(self) -> str | Path:
        return self.server.db_path  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        try:
            client_ip = "-"
            if getattr(self, "client_address", None):
                client_ip = str(self.client_address[0])
            message = format % args if args else format
            logging.getLogger("app.http.access").info(
                "[%s] %s %s",
                self.log_date_time_string(),
                client_ip,
                message,
            )
        except Exception:
            pass

    def do_OPTIONS(self) -> None:
        ctx = RequestContext(self, "OPTIONS")
        ctx.response._handler.send_response(HTTPStatus.NO_CONTENT)
        ctx.response.send_cors_headers()
        ctx.response._handler.end_headers()

    def do_GET(self) -> None:
        self.dispatch("GET")

    def do_POST(self) -> None:
        self.dispatch("POST")

    def do_PUT(self) -> None:
        self.dispatch("PUT")

    def do_PATCH(self) -> None:
        self.dispatch("PATCH")

    def do_DELETE(self) -> None:
        self.dispatch("DELETE")

    def dispatch(self, method: str) -> None:
        logger = logging.getLogger("app.request")
        try:
            ctx = RequestContext(self, method)
            ctx.state["database_summary"] = database_summary
            ctx.state["detect_database_engine"] = detect_database_engine
            if ctx.path.startswith("/api/admin/"):
                require_authenticated(ctx)
            ROUTER.dispatch(ctx)
        except Exception as exc:
            ctx = RequestContext(self, method)
            _dispatch_error_response(ctx, exc, logger)


def run_server(host: str, port: int, db_path: str | Path) -> None:
    if detect_database_engine(db_path) != "postgres":
        raise RuntimeError(
            "后端正式运行仅支持 PostgreSQL。"
            " 如需使用 SQLite，请只在明确的 legacy/test/migration 脚本中显式传入。"
        )
    ensure_prediction_configs_loaded(db_path)
    ensure_admin_tables(db_path)
    init_logging(str(db_path))
    server = ThreadingHTTPServer((host, port), ApiHandler)
    server.db_path = db_path  # type: ignore[attr-defined]
    print(f"Backend API running at http://{host}:{port}")
    print(f"CMS admin page: http://{host}:{port}/admin")
    print(f"Database engine: {detect_database_engine(db_path)} (formal runtime requires PostgreSQL)")
    print(f"Database target: {db_path}")
    scheduler = CrawlerScheduler(db_path)
    scheduler.start()
    try:
        server.serve_forever()
    finally:
        scheduler.stop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Liuhecai backend API and Python CMS.")
    parser.add_argument("--host", default=os.environ.get("LOTTERY_API_HOST", "127.0.0.1"), help="HTTP host.")
    parser.add_argument("--port", type=int, default=int(os.environ.get("LOTTERY_API_PORT", "8000")), help="HTTP port.")
    parser.add_argument(
        "--db-path",
        "--db_path",
        dest="db_path",
        default=DEFAULT_POSTGRES_DSN or None,
        help="PostgreSQL database target for formal runtime. Falls back to DATABASE_URL when omitted.",
    )
    return parser
