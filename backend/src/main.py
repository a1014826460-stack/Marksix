"""Liuhecai Backend - formal entry point.

This is the canonical entry point for starting the backend server.
app.py remains as a thin compatibility entry point.

Usage:
    python backend/src/main.py --host 127.0.0.1 --port 8000
    python backend/src/main.py --host 127.0.0.1 --port 8000 --db-path "postgresql://..."
"""

from __future__ import annotations

from app_http.server import build_parser, run_server
from db import default_postgres_target, is_postgres_target

if __name__ == "__main__":
    args = build_parser().parse_args()
    db_target = args.db_path or default_postgres_target()
    if not is_postgres_target(db_target):
        raise RuntimeError(
            "后端服务启动只接受 PostgreSQL DSN。"
            " 如需使用 SQLite，请改用明确的迁移或测试脚本。"
        )
    run_server(args.host, args.port, db_target)
