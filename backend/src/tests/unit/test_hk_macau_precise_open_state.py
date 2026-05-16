from __future__ import annotations

from pathlib import Path

from crawler import scheduler
from db import connect
from runtime_config import ensure_system_config_table, seed_system_config_defaults
from tables import ensure_admin_tables


def _setup_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "hk_macau_precise_open.sqlite3")
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        ensure_system_config_table(conn)
        seed_system_config_defaults(conn, now="2026-01-01T00:00:00+00:00")
        conn.execute(
            """
            INSERT OR IGNORE INTO lottery_types (id, name, draw_time, collect_url, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                2,
                "澳门彩",
                "21:30",
                "https://www.lnlllt.com/api.php",
                1,
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
            ),
        )
        conn.execute(
            """
            INSERT INTO lottery_draws (
                lottery_type_id, year, term, numbers, draw_time, next_time, status,
                is_opened, next_term, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                2,
                2026,
                134,
                "01,02,03,04,05,06,07",
                "2026-05-14 21:30:00",
                "1778852100000",
                1,
                1,
                135,
                "2026-05-14T13:30:00+00:00",
                "2026-05-14T13:30:00+00:00",
            ),
        )
    return db_path


def test_auto_crawl_does_not_mark_macau_draw_opened_before_precise_open(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)

    monkeypatch.setattr(
        scheduler,
        "_fetch_current_draw_records",
        lambda _db_path, _lt_id: [
            {
                "issue": "135",
                "open_time": "2026-05-15 21:30:00",
                "result": "08,09,10,11,12,13,14",
                "next_time": "1778938500000",
            }
        ],
    )
    monkeypatch.setattr(scheduler, "reset_crawler_fail_count", lambda *args, **kwargs: None)
    monkeypatch.setattr(scheduler, "alert_crawler_failure", lambda *args, **kwargs: None)
    monkeypatch.setattr(scheduler, "alert_draw_staleness", lambda *args, **kwargs: None)
    monkeypatch.setattr(scheduler, "sync_all_lottery_type_next_times", lambda *args, **kwargs: None)
    monkeypatch.setattr(scheduler.CrawlerScheduler, "_reschedule_precise_checks", lambda self: None)
    monkeypatch.setattr(scheduler, "_schedule_backfill_after_draw", lambda *args, **kwargs: None)

    runner = scheduler.CrawlerScheduler(db_path)
    runner._auto_crawl()

    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT is_opened, numbers
            FROM lottery_draws
            WHERE lottery_type_id = ? AND year = ? AND term = ?
            """,
            (2, 2026, 135),
        ).fetchone()
        current_period = conn.execute(
            "SELECT value_text FROM system_config WHERE key = ?",
            ("lottery.macau_current_period",),
        ).fetchone()

    assert row is not None
    assert int(row["is_opened"] or 0) == 0
    assert str(row["numbers"] or "") == "08,09,10,11,12,13,14"
    assert str(current_period["value_text"] or "") == "2026134"


def test_precise_open_marks_latest_macau_draw_opened(tmp_path):
    db_path = _setup_db(tmp_path)

    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO lottery_draws (
                lottery_type_id, year, term, numbers, draw_time, next_time, status,
                is_opened, next_term, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                2,
                2026,
                135,
                "08,09,10,11,12,13,14",
                "2026-05-15 21:30:00",
                "1778938500000",
                1,
                0,
                136,
                "2026-05-15T13:34:47+00:00",
                "2026-05-15T13:34:47+00:00",
            ),
        )

    runner = scheduler.CrawlerScheduler(db_path)
    opened = runner._open_specific_records(2, {"year": 2026, "term": 135})

    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT is_opened
            FROM lottery_draws
            WHERE lottery_type_id = ? AND year = ? AND term = ?
            """,
            (2, 2026, 135),
        ).fetchone()

    assert opened == 1
    assert row is not None
    assert int(row["is_opened"] or 0) == 1
