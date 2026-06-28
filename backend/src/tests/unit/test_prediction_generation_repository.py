from __future__ import annotations

from db import connect
from domains.prediction import generation_repository


def test_generation_repository_loads_opened_draws_and_future_truth_without_exposing_it_by_default(tmp_path):
    db_path = tmp_path / "generation_repository.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE lottery_draws (
                id INTEGER PRIMARY KEY,
                lottery_type_id INTEGER,
                year INTEGER,
                term INTEGER,
                numbers TEXT,
                is_opened INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            INSERT INTO lottery_draws (lottery_type_id, year, term, numbers, is_opened)
            VALUES
                (3, 2026, 130, '01,02,03,04,05,06,07', 1),
                (3, 2026, 131, '08,09,10,11,12,13,14', 0)
            """
        )

        opened = generation_repository.list_opened_draws_in_issue_range(
            conn,
            lottery_type_id=3,
            start_issue=(2026, 129),
            end_issue=(2026, 130),
        )
        truth = generation_repository.get_future_draw_truth(
            conn,
            lottery_type_id=3,
            year=2026,
            term=131,
            zodiac_map={"14": "rabbit"},
            color_map={"14": "blue"},
        )

    assert opened == [{"year": 2026, "term": 130, "numbers_str": "01,02,03,04,05,06,07"}]
    assert truth is not None
    assert truth.special_code == "14"
    assert truth.special_zodiac == "rabbit"
    assert truth.special_color == "blue"
    assert truth.to_safe_dict() == {"has_truth": True}


def test_generation_repository_loads_enabled_site_modules_with_requested_filter(tmp_path):
    db_path = tmp_path / "generation_modules.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE site_prediction_modules (
                id INTEGER PRIMARY KEY,
                site_id INTEGER,
                mechanism_key TEXT,
                mode_id INTEGER,
                status INTEGER,
                sort_order INTEGER
            )
            """
        )
        conn.execute(
            """
            INSERT INTO site_prediction_modules (site_id, mechanism_key, mode_id, status, sort_order)
            VALUES
                (7, 'pt3xiao', 43, 1, 20),
                (7, 'daxiao', 57, 1, 10),
                (7, 'disabled', 99, 0, 30)
            """
        )

        rows = generation_repository.list_enabled_site_prediction_modules(
            conn,
            site_id=7,
            mechanism_keys=["pt3xiao"],
        )

    assert rows == [
        {
            "id": 1,
            "mechanism_key": "pt3xiao",
            "mode_id": 43,
            "status": 1,
            "sort_order": 20,
        }
    ]
