from __future__ import annotations


def _setup(tmp_path):
    from database.bootstrap import ensure_admin_tables
    from db import connect

    db_path = str(tmp_path / "scheduler-publication.sqlite3")
    ensure_admin_tables(db_path)
    return db_path


def _insert_draw(db_path, lottery_type_id, year, term):
    from db import connect

    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO lottery_draws (
                lottery_type_id, year, term, numbers, draw_time, status,
                is_opened, next_term, created_at, updated_at
            ) VALUES (?, ?, ?, '01,02,03,04,05,06,07', '2026-01-01 21:30:00', 1, 0, ?, ?, ?)
            """,
            (lottery_type_id, year, term, term + 1, "2026-01-01T13:30:00+00:00", "2026-01-01T13:30:00+00:00"),
        )


def _events(db_path):
    from db import connect
    with connect(db_path) as conn:
        return [dict(row) for row in conn.execute("SELECT event_key, event_type FROM publication_outbox ORDER BY id").fetchall()]


def test_specific_scheduler_open_enqueues_in_same_draw_transaction(tmp_path):
    from crawler.scheduler import CrawlerScheduler

    db_path = _setup(tmp_path)
    _insert_draw(db_path, 2, 2026, 135)

    assert CrawlerScheduler(db_path)._open_specific_records(2, {"year": 2026, "term": 135}) == 1
    assert _events(db_path) == [{"event_key": "draw-published:2:2026:135", "event_type": "draw.published"}]


def test_auto_scheduler_open_enqueues_each_due_draw(tmp_path):
    from crawler.scheduler import CrawlerScheduler

    db_path = _setup(tmp_path)
    _insert_draw(db_path, 1, 2026, 100)

    CrawlerScheduler(db_path)._auto_open_draws()
    assert _events(db_path) == [{"event_key": "draw-published:1:2026:100", "event_type": "draw.published"}]


def test_taiwan_scheduler_open_enqueues_before_next_time_calculation_commits(tmp_path):
    from crawler.scheduler import CrawlerScheduler

    db_path = _setup(tmp_path)
    _insert_draw(db_path, 3, 2026, 188)

    assert CrawlerScheduler(db_path)._open_taiwan_draws_and_update_next_time() == 1
    assert _events(db_path) == [{"event_key": "draw-published:3:2026:188", "event_type": "draw.published"}]
