from __future__ import annotations

from datetime import datetime, timezone


def test_lottery_draw_health_marks_only_expired_latest_opened_draws_stale(tmp_path):
    from domains.lottery.service import get_lottery_draw_health
    from tables import ensure_admin_tables
    from db import connect

    db_path = str(tmp_path / "lottery-health.sqlite3")
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        now = "2026-07-20T10:00:00+00:00"
        conn.execute(
            """
            INSERT INTO lottery_types (id, name, draw_time, status, created_at, updated_at)
            VALUES (101, '测试过期彩种', '21:30', 1, ?, ?)
            """,
            (now, now),
        )
        conn.execute(
            """
            INSERT INTO lottery_types (id, name, draw_time, status, created_at, updated_at)
            VALUES (102, '测试正常彩种', '21:30', 1, ?, ?)
            """,
            (now, now),
        )
        conn.execute(
            """
            INSERT INTO lottery_draws (
                lottery_type_id, year, term, numbers, draw_time, status, is_opened,
                next_term, next_time, created_at, updated_at
            ) VALUES (101, 2026, 77, '01,02,03,04,05,06,07', '2026-07-18 21:30:00', 1, 1, 78, '1784361600000', ?, ?)
            """,
            (now, now),
        )
        conn.execute(
            """
            INSERT INTO lottery_draws (
                lottery_type_id, year, term, numbers, draw_time, status, is_opened,
                next_term, next_time, created_at, updated_at
            ) VALUES (102, 2026, 78, '01,02,03,04,05,06,07', '2026-07-20 21:30:00', 1, 1, 79, '1784635200000', ?, ?)
            """,
            (now, now),
        )

    payload = get_lottery_draw_health(
        db_path,
        now=datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc),
    )

    assert payload["status"] == "degraded"
    assert payload["stale_lottery_type_ids"] == [101]
    reported = {
        item["lottery_type_id"]: item
        for item in payload["lotteries"]
        if item["lottery_type_id"] in {101, 102}
    }
    assert reported == {
        101: {
            "lottery_type_id": 101,
            "lottery_name": "测试过期彩种",
            "current_issue": "202677",
            "next_time": "1784361600000",
            "stale": True,
        },
        102: {
            "lottery_type_id": 102,
            "lottery_name": "测试正常彩种",
            "current_issue": "202678",
            "next_time": "1784635200000",
            "stale": False,
        },
    }
