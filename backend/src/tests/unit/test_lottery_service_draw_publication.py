from __future__ import annotations


def _payload(*, opened: bool, numbers: str = "01,02,03,04,05,06,07"):
    return {
        "lottery_type_id": 3,
        "year": 2026,
        "term": 188,
        "numbers": numbers,
        "draw_time": "2026-08-01 22:30:00",
        "next_time": "1767277800000",
        "status": True,
        "is_opened": opened,
        "next_term": 189,
    }


def test_lottery_save_draw_enqueues_when_an_admin_creates_an_opened_draw(tmp_path):
    from database.bootstrap import ensure_admin_tables
    from db import connect
    from domains.lottery.service import save_draw

    db_path = str(tmp_path / "service-draw-publication.sqlite3")
    ensure_admin_tables(db_path)
    save_draw(db_path, _payload(opened=True))

    with connect(db_path) as conn:
        events = conn.execute("SELECT event_key, event_type FROM publication_outbox").fetchall()

    assert [dict(row) for row in events] == [
        {"event_key": "draw-published:3:2026:188", "event_type": "draw.published"},
    ]


