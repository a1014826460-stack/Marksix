from __future__ import annotations


def _setup(tmp_path):
    from database.bootstrap import ensure_admin_tables
    from db import connect

    db_path = str(tmp_path / "collector-publication.sqlite3")
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO lottery_types (id, name, status, created_at, updated_at) VALUES (2, '澳门彩', 1, ?, ?)",
            ("2026-08-07T14:00:00+00:00", "2026-08-07T14:00:00+00:00"),
        )
    return db_path


def test_collector_upsert_enqueues_initial_and_corrected_opened_draw_events(tmp_path):
    from crawler.collectors import _upsert_draw
    from db import connect

    db_path = _setup(tmp_path)
    with connect(db_path) as conn:
        _upsert_draw(conn, 2, 2026, 135, "01,02,03,04,05,06,07", "2026-08-07 21:30:00", 1, "2026-08-07T14:32:00+00:00")
        _upsert_draw(conn, 2, 2026, 135, "08,09,10,11,12,13,14", "2026-08-07 21:30:00", 1, "2026-08-07T14:33:00+00:00")
        rows = conn.execute("SELECT event_key, event_type FROM publication_outbox ORDER BY id").fetchall()

    assert [dict(row) for row in rows] == [
        {"event_key": "draw-published:2:2026:135", "event_type": "draw.published"},
        {"event_key": "draw-refresh:2:2026:135:1", "event_type": "draw.refresh"},
    ]

def test_collector_unopened_upsert_does_not_enqueue_until_it_is_opened(tmp_path):
    from crawler.collectors import _upsert_draw
    from db import connect

    db_path = _setup(tmp_path)
    with connect(db_path) as conn:
        _upsert_draw(conn, 2, 2026, 135, "01,02,03,04,05,06,07", "2026-08-07 21:30:00", 0, "2026-08-07T14:30:00+00:00")
        _upsert_draw(conn, 2, 2026, 135, "01,02,03,04,05,06,07", "2026-08-07 21:30:00", 1, "2026-08-07T14:32:00+00:00")
        rows = conn.execute("SELECT event_key, event_type FROM publication_outbox ORDER BY id").fetchall()

    assert [dict(row) for row in rows] == [
        {"event_key": "draw-published:2:2026:135", "event_type": "draw.published"},
    ]
