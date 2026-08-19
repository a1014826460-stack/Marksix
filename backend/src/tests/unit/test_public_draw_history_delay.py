from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import public.api as public_api
import helpers
import runtime_config
from db import connect


BEIJING = timezone(timedelta(hours=8))


def _setup_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "public_draw_history_delay.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE lottery_draws (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lottery_type_id INTEGER,
                year INTEGER,
                term INTEGER,
                numbers TEXT,
                draw_time TEXT,
                is_opened INTEGER
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
            INSERT INTO lottery_draws
                (lottery_type_id, year, term, numbers, draw_time, is_opened)
            VALUES
                (3, 2026, 99, '01,02,03,04,05,06,07', '2026-08-19 21:00:00', 1),
                (3, 2026, 100, '08,09,10,11,12,13,14', '2026-08-19 22:32:00', 1)
            """
        )
        conn.commit()
    return db_path


def test_draw_history_hides_current_issue_until_four_minutes_after_draw(tmp_path: Path, monkeypatch):
    db_path = _setup_db(tmp_path)

    monkeypatch.setattr(
        public_api,
        "beijing_now",
        lambda: datetime(2026, 8, 19, 22, 35, 59, tzinfo=BEIJING),
    )
    before_unlock = public_api.get_draw_history(db_path, lottery_type=3, year=2026)
    assert [item["issue"] for item in before_unlock["items"]] == ["99"]

    monkeypatch.setattr(
        public_api,
        "beijing_now",
        lambda: datetime(2026, 8, 19, 22, 36, 0, tzinfo=BEIJING),
    )
    at_unlock = public_api.get_draw_history(db_path, lottery_type=3, year=2026)
    assert [item["issue"] for item in at_unlock["items"]] == ["100", "99"]


def test_history_backfill_default_is_four_minutes():
    assert runtime_config.CONFIG_DEFAULTS["history_backfill_delay_after_draw"]["value"] == 4


def test_legacy_history_overlay_unlocks_at_exactly_four_minutes(monkeypatch):
    monkeypatch.setattr(
        helpers,
        "beijing_now",
        lambda: datetime(2026, 8, 19, 22, 36, 0, tzinfo=BEIJING),
    )
    monkeypatch.setattr(runtime_config, "get_config_from_conn", lambda _conn, _key, _default: 4)

    assert helpers._history_result_visible_after_delay(
        object(),
        {
            "is_opened": 1,
            "draw_time": "2026-08-19 22:32:00",
        },
    )


def test_legacy_history_overlay_uses_fixed_window_despite_stale_config(monkeypatch):
    monkeypatch.setattr(
        helpers,
        "beijing_now",
        lambda: datetime(2026, 8, 19, 22, 36, 0, tzinfo=BEIJING),
    )
    monkeypatch.setattr(runtime_config, "get_config_from_conn", lambda _conn, _key, _default: 60)

    assert helpers._history_result_visible_after_delay(
        object(),
        {
            "is_opened": 1,
            "draw_time": "2026-08-19 22:32:00",
        },
    )
