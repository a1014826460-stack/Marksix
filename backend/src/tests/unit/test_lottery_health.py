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


def test_lottery_draw_health_reports_taiwan_future_issue_holes(tmp_path):
    from db import connect
    from domains.lottery.service import get_lottery_draw_health
    from tables import ensure_admin_tables

    db_path = str(tmp_path / "taiwan-continuity-health.sqlite3")
    ensure_admin_tables(db_path)
    now = "2026-08-10T14:33:00+00:00"
    with connect(db_path) as conn:
        conn.execute(
            "UPDATE lottery_types SET name = '台湾彩', draw_time = '22:32', status = 1, updated_at = ? WHERE id = 3",
            (now,),
        )
        for term, opened in ((222, 1), (224, 0), (225, 0), (227, 0)):
            conn.execute(
                """
                INSERT INTO lottery_draws (
                    lottery_type_id, year, term, numbers, draw_time, status, is_opened,
                    next_term, next_time, created_at, updated_at
                ) VALUES (3, 2026, ?, '01,02,03,04,05,06,07', ?, 1, ?, ?, '1790000000000', ?, ?)
                """,
                (term, f"2026-08-{term - 212:02d} 22:32:00", opened, term + 1, now, now),
            )

    payload = get_lottery_draw_health(
        db_path, now=datetime(2026, 8, 10, 14, 33, tzinfo=timezone.utc),
    )

    assert payload["status"] == "degraded"
    assert payload["taiwan_continuity"] == {
        "continuous": False,
        "latest_opened_issue": "2026222",
        "checked_through_issue": "2026234",
        "missing_issues": [
            "2026223", "2026226", "2026228", "2026229", "2026230",
            "2026231", "2026232", "2026233", "2026234",
        ],
        "duplicate_issues": [],
    }


def test_taiwan_continuity_health_checks_configured_coverage_across_year_rollover(tmp_path):
    from db import connect
    from domains.lottery.service import get_lottery_draw_health
    from tables import ensure_admin_tables

    db_path = str(tmp_path / "taiwan-rollover-health.sqlite3")
    ensure_admin_tables(db_path)
    now = "2026-12-31T14:33:00+00:00"
    with connect(db_path) as conn:
        conn.execute(
            "UPDATE system_config SET value_text = '3' WHERE key = 'taiwan_future_autofill.count'"
        )
        for year, term, opened in ((2026, 365, 1), (2027, 1, 0), (2027, 3, 0)):
            conn.execute(
                """
                INSERT INTO lottery_draws (
                    lottery_type_id, year, term, numbers, draw_time, status, is_opened,
                    next_term, next_time, created_at, updated_at
                ) VALUES (3, ?, ?, '01,02,03,04,05,06,07', '2027-01-01 22:32:00', 1, ?, ?, '1790000000000', ?, ?)
                """,
                (year, term, opened, term + 1, now, now),
            )

    continuity = get_lottery_draw_health(
        db_path, now=datetime(2026, 12, 31, 14, 33, tzinfo=timezone.utc),
    )["taiwan_continuity"]

    assert continuity == {
        "continuous": False,
        "latest_opened_issue": "2026365",
        "checked_through_issue": "2027003",
        "missing_issues": ["2027002"],
        "duplicate_issues": [],
    }
