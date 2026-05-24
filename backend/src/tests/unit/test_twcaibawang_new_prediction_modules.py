from __future__ import annotations

from database.schema.legacy import ensure_twcaibawang_prediction_tables
from db import auto_increment_primary_key, connect
from predict.common import load_fixed_value_map
from predict.mechanisms import get_prediction_config


def test_twcaibawang_new_mode_tables_are_bootstrapped(tmp_path):
    db_path = str(tmp_path / "twcaibawang_new_modes.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_tables (
                modes_id INTEGER PRIMARY KEY,
                filename TEXT,
                title TEXT,
                table_name TEXT,
                record_count INTEGER,
                is_image INTEGER,
                is_text INTEGER,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        ensure_twcaibawang_prediction_tables(conn, auto_increment_primary_key("id", conn.engine))

        basic_columns = set(conn.table_columns("mode_payload_479"))
        xiao_code_columns = set(conn.table_columns("mode_payload_484"))
        row_479 = conn.execute(
            "SELECT title, table_name FROM mode_payload_tables WHERE modes_id = ?",
            (479,),
        ).fetchone()
        row_484 = conn.execute(
            "SELECT title, table_name FROM mode_payload_tables WHERE modes_id = ?",
            (484,),
        ).fetchone()

    assert {"content", "source_record_id"}.issubset(basic_columns)
    assert {"content", "xiao", "code", "source_record_id"}.issubset(xiao_code_columns)
    assert row_479["table_name"] == "mode_payload_479"
    assert row_484["table_name"] == "mode_payload_484"


def test_twcaibawang_new_modes_are_registered_in_mechanisms():
    assert get_prediction_config("siduanzhongte").default_modes_id == 479
    assert get_prediction_config("xiongjiliuxiao").default_modes_id == 480
    assert get_prediction_config("wensha10ma").default_modes_id == 481
    assert get_prediction_config("sihangzhongte").default_modes_id == 482
    assert get_prediction_config("sitouzhongte").default_modes_id == 483
    assert get_prediction_config("liuxiao18ma").default_modes_id == 484


def test_twcaibawang_group_label_fallbacks_are_human_readable(tmp_path):
    db_path = str(tmp_path / "twcaibawang_fixed_data.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE fixed_data (
                id INTEGER PRIMARY KEY,
                name TEXT,
                code TEXT,
                sign TEXT
            )
            """
        )

        segment_map = load_fixed_value_map(conn, "7段", tuple(f"{index}段" for index in range(1, 8)))
        xiongji_map = load_fixed_value_map(conn, "凶丑吉美生肖", ("凶丑", "吉美"))

    assert tuple(segment_map.keys()) == tuple(f"{index}段" for index in range(1, 8))
    assert tuple(xiongji_map.keys()) == ("凶丑", "吉美")
