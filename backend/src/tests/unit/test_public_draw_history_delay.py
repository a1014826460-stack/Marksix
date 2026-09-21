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


def test_draw_history_hides_current_issue_until_configured_delay_after_draw(
    tmp_path: Path, monkeypatch
):
    db_path = _setup_db(tmp_path)
    # 未显式配置时使用默认闸门 8 分钟：22:32 开奖 → 22:40 才可见。
    monkeypatch.setattr(runtime_config, "get_config", lambda _db, _key, default: default)

    monkeypatch.setattr(
        public_api,
        "beijing_now",
        lambda: datetime(2026, 8, 19, 22, 39, 59, tzinfo=BEIJING),
    )
    before_unlock = public_api.get_draw_history(db_path, lottery_type=3, year=2026)
    assert [item["issue"] for item in before_unlock["items"]] == ["99"]

    monkeypatch.setattr(
        public_api,
        "beijing_now",
        lambda: datetime(2026, 8, 19, 22, 40, 0, tzinfo=BEIJING),
    )
    at_unlock = public_api.get_draw_history(db_path, lottery_type=3, year=2026)
    assert [item["issue"] for item in at_unlock["items"]] == ["100", "99"]


def test_draw_history_unlock_follows_system_config_delay(tmp_path: Path, monkeypatch):
    db_path = _setup_db(tmp_path)
    monkeypatch.setattr(runtime_config, "get_config", lambda _db, _key, _default: 30)

    monkeypatch.setattr(
        public_api,
        "beijing_now",
        lambda: datetime(2026, 8, 19, 23, 1, 59, tzinfo=BEIJING),
    )
    assert [
        item["issue"]
        for item in public_api.get_draw_history(db_path, lottery_type=3, year=2026)["items"]
    ] == ["99"]

    monkeypatch.setattr(
        public_api,
        "beijing_now",
        lambda: datetime(2026, 8, 19, 23, 2, 0, tzinfo=BEIJING),
    )
    assert [
        item["issue"]
        for item in public_api.get_draw_history(db_path, lottery_type=3, year=2026)["items"]
    ] == ["100", "99"]


def test_history_backfill_default_is_eight_minutes():
    assert runtime_config.CONFIG_DEFAULTS["history_backfill_delay_after_draw"]["value"] == 8


def test_legacy_history_overlay_unlocks_at_exactly_configured_delay(monkeypatch):
    monkeypatch.setattr(
        helpers,
        "beijing_now",
        lambda: datetime(2026, 8, 19, 22, 40, 0, tzinfo=BEIJING),
    )
    monkeypatch.setattr(runtime_config, "get_config_from_conn", lambda _conn, _key, _default: 8)

    assert helpers._history_result_visible_after_delay(
        object(),
        {
            "is_opened": 1,
            "draw_time": "2026-08-19 22:32:00",
        },
    )


def test_legacy_history_overlay_follows_system_config_delay(monkeypatch):
    monkeypatch.setattr(
        helpers,
        "beijing_now",
        lambda: datetime(2026, 8, 19, 22, 52, 0, tzinfo=BEIJING),
    )
    monkeypatch.setattr(runtime_config, "get_config_from_conn", lambda _conn, _key, _default: 60)

    assert not helpers._history_result_visible_after_delay(
        object(),
        {
            "is_opened": 1,
            "draw_time": "2026-08-19 22:32:00",
        },
    )
    assert helpers._history_result_visible_after_delay(
        object(),
        {
            "is_opened": 1,
            "draw_time": "2026-08-19 21:00:00",
        },
    )
