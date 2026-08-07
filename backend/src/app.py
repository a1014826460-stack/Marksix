"""Lightweight backend API and CMS for lottery data management.

This is a thin compatibility entry point. See main.py for the canonical entry point.
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
