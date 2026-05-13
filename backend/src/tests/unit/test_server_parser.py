from __future__ import annotations

import sys
from pathlib import Path


_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from app_http.server import build_parser


def test_build_parser_allows_missing_database_url_when_cli_db_path_is_provided(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    parser = build_parser()

    args = parser.parse_args(["--db-path", "postgresql://postgres:test@localhost:5432/liuhecai"])

    assert args.db_path == "postgresql://postgres:test@localhost:5432/liuhecai"


def test_build_parser_accepts_legacy_db_path_alias(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    parser = build_parser()

    args = parser.parse_args(["--db_path", "postgresql://postgres:test@localhost:5432/liuhecai"])

    assert args.db_path == "postgresql://postgres:test@localhost:5432/liuhecai"
