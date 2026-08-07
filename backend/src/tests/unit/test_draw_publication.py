from __future__ import annotations


def _connection(tmp_path):
    from database.bootstrap import ensure_admin_tables
    from db import connect

    db_path = str(tmp_path / "draw_publication.sqlite3")
    ensure_admin_tables(db_path)
    return connect(db_path)


def _draw(*, opened: int, numbers: str = "01,02,03,04,05,06,07"):
    return {
        "lottery_type_id": 3,
        "year": 2026,
        "term": 188,
        "numbers": numbers,
        "draw_time": "2026-08-07 22:32:00",
        "next_time": "1786141920000",
        "status": 1,
        "is_opened": opened,
    }


def test_newly_opened_draw_enqueues_the_single_initial_publication_event(tmp_path):
    from outbox.draw_publication import enqueue_draw_publication

    with _connection(tmp_path) as conn:
        event = enqueue_draw_publication(conn, previous=_draw(opened=0), current=_draw(opened=1), now="2026-08-07T14:32:00+00:00")
        duplicate = enqueue_draw_publication(conn, previous=_draw(opened=0), current=_draw(opened=1), now="2026-08-07T14:32:01+00:00")
        rows = conn.execute("SELECT event_key, event_type FROM publication_outbox").fetchall()

    assert event == "draw.published"
    assert duplicate == "draw.published"
    assert [dict(row) for row in rows] == [{"event_key": "draw-published:3:2026:188", "event_type": "draw.published"}]


def test_opened_draw_correction_enqueues_monotonic_refresh_events(tmp_path):
    from outbox.draw_publication import enqueue_draw_publication

    with _connection(tmp_path) as conn:
        assert enqueue_draw_publication(conn, previous=None, current=_draw(opened=1), now="2026-08-07T14:32:00+00:00") == "draw.published"
        assert enqueue_draw_publication(conn, previous=_draw(opened=1), current=_draw(opened=1, numbers="08,09,10,11,12,13,14"), now="2026-08-07T14:33:00+00:00") == "draw.refresh"
        assert enqueue_draw_publication(conn, previous=_draw(opened=1, numbers="08,09,10,11,12,13,14"), current=_draw(opened=1), now="2026-08-07T14:34:00+00:00") == "draw.refresh"
        rows = conn.execute("SELECT event_key, event_type FROM publication_outbox ORDER BY id").fetchall()

    assert [dict(row) for row in rows] == [
        {"event_key": "draw-published:3:2026:188", "event_type": "draw.published"},
        {"event_key": "draw-refresh:3:2026:188:1", "event_type": "draw.refresh"},
        {"event_key": "draw-refresh:3:2026:188:2", "event_type": "draw.refresh"},
    ]


def test_unopened_draw_never_enqueues_a_publication_event(tmp_path):
    from outbox.draw_publication import enqueue_draw_publication

    with _connection(tmp_path) as conn:
        assert enqueue_draw_publication(conn, previous=None, current=_draw(opened=0)) is None
        rows = conn.execute("SELECT event_key FROM publication_outbox").fetchall()

    assert rows == []
