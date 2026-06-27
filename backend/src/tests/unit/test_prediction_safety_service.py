from __future__ import annotations

from pathlib import Path

from db import connect
from domains.prediction.safety_service import (
    apply_prediction_row_safety,
    lookup_draw_visibility,
    resolve_prediction_request_safety,
)
from tables import ensure_admin_tables


def _setup_draw_db(tmp_path: Path, *, is_opened: int) -> str:
    db_path = str(tmp_path / "prediction_safety.sqlite3")
    ensure_admin_tables(db_path)
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
                3,
                2026,
                188,
                "01,02,03,04,05,06,07",
                "2026-06-27 21:30:00",
                "1782570600000",
                1,
                is_opened,
                189,
                "2026-06-27T13:30:00+00:00",
                "2026-06-27T13:30:00+00:00",
            ),
        )
    return db_path


def test_hidden_draw_blocks_request_res_code_and_redacts_row_results(tmp_path: Path):
    db_path = _setup_draw_db(tmp_path, is_opened=0)

    with connect(db_path) as conn:
        effective_res_code, safety = resolve_prediction_request_safety(
            conn,
            lottery_type="3",
            year="2026",
            term="188",
            res_code="01,02,03,04,05,06,07",
        )
        row = apply_prediction_row_safety(
            conn,
            {
                "content": "sample",
                "res_code": "01,02,03,04,05,06,07",
                "res_sx": "鼠,牛,虎,兔,龙,蛇,马",
                "res_color": "red,blue,green",
            },
            lottery_type="3",
            year="2026",
            term="188",
        )

    assert effective_res_code is None
    assert safety["result_visibility"] == "hidden"
    assert row == {
        "content": "sample",
        "res_code": "",
        "res_sx": "",
        "res_color": "",
    }


def test_visible_draw_allows_request_res_code_and_keeps_row_results(tmp_path: Path):
    db_path = _setup_draw_db(tmp_path, is_opened=1)

    with connect(db_path) as conn:
        effective_res_code, safety = resolve_prediction_request_safety(
            conn,
            lottery_type="3",
            year="2026",
            term="188",
            res_code="01,02,03,04,05,06,07",
        )
        visibility = lookup_draw_visibility(
            conn,
            lottery_type="3",
            year="2026",
            term="188",
        )
        row = apply_prediction_row_safety(
            conn,
            {
                "content": "sample",
                "res_code": "01,02,03,04,05,06,07",
                "res_sx": "鼠,牛,虎,兔,龙,蛇,马",
                "res_color": "red,blue,green",
            },
            lottery_type="3",
            year="2026",
            term="188",
        )

    assert effective_res_code == "01,02,03,04,05,06,07"
    assert safety["result_visibility"] == "visible"
    assert visibility["result_visibility"] == "visible"
    assert row["res_code"] == "01,02,03,04,05,06,07"
    assert row["res_sx"] == "鼠,牛,虎,兔,龙,蛇,马"
    assert row["res_color"] == "red,blue,green"
