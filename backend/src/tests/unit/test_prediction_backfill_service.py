from __future__ import annotations

from db import connect
from tables import ensure_admin_tables


def _insert_draw(conn, *, lottery_type_id: int, year: int, term: int, numbers: str, is_opened: int) -> None:
    conn.execute(
        """
        INSERT INTO lottery_draws (
            lottery_type_id, year, term, numbers, draw_time, next_time, status,
            is_opened, next_term, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            lottery_type_id,
            year,
            term,
            numbers,
            f"{year}-06-27 22:30:00",
            "",
            1,
            is_opened,
            term + 1,
            "2026-06-27T00:00:00+00:00",
            "2026-06-27T00:00:00+00:00",
        ),
    )


def test_backfill_service_resolves_recent_issue_range_and_opened_draws(tmp_path, monkeypatch):
    from domains.prediction import backfill_service

    db_path = tmp_path / "prediction-backfill.sqlite3"
    ensure_admin_tables(db_path)

    with connect(db_path) as conn:
        _insert_draw(conn, lottery_type_id=3, year=2026, term=126, numbers="01,02,03,04,05,06,07", is_opened=1)
        _insert_draw(conn, lottery_type_id=3, year=2026, term=127, numbers="08,09,10,11,12,13,14", is_opened=1)
        _insert_draw(conn, lottery_type_id=3, year=2026, term=128, numbers="15,16,17,18,19,20,21", is_opened=0)
        _insert_draw(conn, lottery_type_id=2, year=2026, term=200, numbers="22,23,24,25,26,27,28", is_opened=1)

    monkeypatch.setattr(backfill_service, "_get_config", lambda conn, key, default: 365)

    with connect(db_path) as conn:
        start_issue, end_issue = backfill_service.resolve_backfill_issue_range(
            conn,
            lottery_type_id=3,
            start_issue="",
            end_issue="",
            recent_count=2,
        )
        draws = backfill_service.list_opened_draws_for_issue_range(
            conn,
            lottery_type_id=3,
            start_year=2026,
            start_term=126,
            end_year=2026,
            end_term=127,
        )

    assert (start_issue, end_issue) == ("2026126", "2026127")
    assert draws == [
        {"year": 2026, "term": 126, "numbers": "01,02,03,04,05,06,07"},
        {"year": 2026, "term": 127, "numbers": "08,09,10,11,12,13,14"},
    ]


def test_backfill_service_rejects_missing_opened_draw_for_recent_range(tmp_path):
    from domains.prediction import backfill_service

    db_path = tmp_path / "prediction-backfill-empty.sqlite3"
    ensure_admin_tables(db_path)

    with connect(db_path) as conn:
        try:
            backfill_service.resolve_backfill_issue_range(
                conn,
                lottery_type_id=3,
                start_issue="",
                end_issue="",
                recent_count=1,
            )
        except ValueError as exc:
            assert str(exc) == "没有已开奖记录，无法推算期号范围"
        else:
            raise AssertionError("missing opened draw should fail")
