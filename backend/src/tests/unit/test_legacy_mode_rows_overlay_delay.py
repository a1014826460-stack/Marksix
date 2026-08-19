from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import helpers
from db import connect
from legacy.api import load_legacy_mode_rows
from runtime_config import ensure_system_config_table, seed_system_config_defaults


def _setup_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "legacy_mode_rows_overlay_delay.sqlite3")
    with connect(db_path) as conn:
        ensure_system_config_table(conn)
        seed_system_config_defaults(conn, now="2026-01-01T00:00:00+00:00")
        conn.execute(
            """
            CREATE TABLE mode_payload_tables (
                modes_id INTEGER PRIMARY KEY,
                title TEXT,
                table_name TEXT NOT NULL,
                record_count INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE mode_payload_152 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year TEXT,
                term TEXT,
                web INTEGER,
                type INTEGER,
                content TEXT,
                res_code TEXT,
                res_sx TEXT,
                res_color TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE fixed_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sign TEXT,
                name TEXT,
                code TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE lottery_draws (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lottery_type_id INTEGER,
                year INTEGER,
                term INTEGER,
                numbers TEXT,
                draw_time TEXT,
                next_time TEXT,
                status INTEGER,
                is_opened INTEGER,
                next_term INTEGER,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )

        conn.execute(
            "INSERT INTO mode_payload_tables (modes_id, title, table_name, record_count) VALUES (?, ?, ?, ?)",
            (152, "ZYX", "mode_payload_152", 2),
        )
        conn.execute(
            """
            INSERT INTO mode_payload_152 (year, term, web, type, content, res_code, res_sx, res_color)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "2026", "53", 6, 1, '["A"]', "", "", "",
                "2026", "54", 6, 1, '["B"]', "", "", "",
            ),
        )
        conn.execute(
            """
            INSERT INTO lottery_draws (
                lottery_type_id, year, term, numbers, draw_time, next_time, status,
                is_opened, next_term, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1, 2026, 53, "01,13,22,34,45,49", "2026-05-20 11:30:00", "", 1, 1, 54,
                "2026-05-20T03:30:00+00:00", "2026-05-20T03:30:00+00:00",
                1, 2026, 54, "02,14,23,35,46,48", "2026-05-20 11:50:00", "", 1, 1, 55,
                "2026-05-20T03:50:00+00:00", "2026-05-20T03:50:00+00:00",
            ),
        )
        conn.execute(
            "UPDATE system_config SET value_text = ? WHERE key = ?",
            ("15", "history_backfill_delay_after_draw"),
        )
        conn.commit()
    return db_path


def test_load_legacy_mode_rows_only_exposes_results_after_delay(tmp_path: Path, monkeypatch):
    db_path = _setup_db(tmp_path)
    fixed_now = datetime(2026, 5, 20, 12, 31, 0, tzinfo=timezone(timedelta(hours=8)))
    monkeypatch.setattr(helpers, "beijing_now", lambda: fixed_now)

    payload = load_legacy_mode_rows(
        db_path,
        modes_id=152,
        limit=10,
        web=6,
        type_value=1,
    )

    rows = payload["rows"]
    row_53 = next(row for row in rows if str(row.get("term")) == "53")
    row_54 = next(row for row in rows if str(row.get("term")) == "54")

    assert row_53["res_code"] == "01,13,22,34,45,49"
    assert row_54["res_code"] == ""
    assert row_54["res_sx"] == ""
    assert row_54["res_color"] == ""
