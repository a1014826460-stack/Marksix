"""Liuhecai Backend - formal entry point.

This is the canonical entry point for starting the backend server.
app.py remains as a thin compatibility entry point.

Usage:
    python backend/src/main.py --host 127.0.0.1 --port 8000
    python backend/src/main.py --host 127.0.0.1 --port 8000 --db-path "postgresql://..."
"""

from __future__ import annotations

from app_http.server import build_parser, run_server
from database.runtime_targets import resolve_database_targets
from runtime_environment import validate_runtime_database_target

if __name__ == "__main__":
    args = build_parser().parse_args()
    targets = resolve_database_targets(explicit_write=args.db_path)
    validate_runtime_database_target(targets.write)
    validate_runtime_database_target(targets.read)
    run_server(args.host, args.port, targets)
