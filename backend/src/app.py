"""Lightweight backend API and CMS for lottery data management."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = Path(__file__).resolve().parent
PREDICT_ROOT = SRC_ROOT / "predict"
UTILS_ROOT = SRC_ROOT / "utils"
CRAWLER_ROOT = SRC_ROOT / "crawler"

for path in (SRC_ROOT, PREDICT_ROOT, UTILS_ROOT, CRAWLER_ROOT):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from crawler.crawler_service import CrawlerScheduler
from db import DEFAULT_POSTGRES_DSN, default_postgres_target, detect_database_engine, is_postgres_target
from http.auth import get_current_user, require_authenticated
from http.request_context import RequestContext
from http.router import Router
from logger import init_logging
from predict.mechanisms import ensure_prediction_configs_loaded
from runtime_config import get_bootstrap_config_value

# Keep old absolute-import callers (e.g. tables.py, admin/*) sharing the same
# PREDICTION_CONFIGS dict — must be set before any module that does
# `from mechanisms import ...` is imported.
sys.modules["mechanisms"] = sys.modules["predict.mechanisms"]

from tables import database_summary, ensure_admin_tables

from routes import (
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

LEGACY_IMAGES_DIR = BACKEND_ROOT / str(get_bootstrap_config_value("legacy.images_dir", "data/Images"))
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
    job_routes.register(router)
    return router


ROUTER = build_router()


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "LiuhecaiBackend/1.0"

    @property
    def db_path(self) -> str | Path:
        return self.server.db_path  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {self.address_string()} {format % args}")

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
        ctx = RequestContext(self, method)
        ctx.state["database_summary"] = database_summary
        ctx.state["detect_database_engine"] = detect_database_engine
        if ctx.path.startswith("/api/admin/"):
            require_authenticated(ctx)
        ROUTER.dispatch(ctx)


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
        default=default_postgres_target(),
        help="PostgreSQL database target for formal runtime.",
    )
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    if args.db_path and not is_postgres_target(args.db_path):
        raise RuntimeError(
            "后端服务启动只接受 PostgreSQL DSN。"
            " 如需使用 SQLite，请改用明确的迁移或测试脚本。"
        )
    run_server(args.host, args.port, args.db_path)
