from __future__ import annotations

from pathlib import Path

from db import connect
from legacy.frontend_compat import handle_frontend_kaijiang_api


def _setup_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "legacy_contract.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_tables (
                modes_id INTEGER PRIMARY KEY,
                table_name TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO mode_payload_tables (modes_id, table_name) VALUES (?, ?)",
            (251, "mode_payload_251"),
        )
        conn.execute(
            """
            CREATE TABLE mode_payload_251 (
                year TEXT,
                term TEXT,
                web INTEGER,
                type INTEGER,
                content TEXT,
                xiao TEXT,
                code TEXT,
                res_code TEXT,
                res_sx TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO mode_payload_251 (
                year, term, web, type, content, xiao, code, res_code, res_sx
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "2026",
                "12",
                6,
                3,
                '["鼠|05,17"]',
                "鼠,牛,虎,兔",
                "01,02",
                "01,02,03,04,05,06,07",
                "鼠,牛,虎,兔,龙,蛇,马",
            ),
        )
        conn.commit()
    return db_path


def test_legacy_result_keeps_data_wrapper(tmp_path: Path):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        result = handle_frontend_kaijiang_api(
            "/api/kaijiang/getJyxiao2",
            {"web": ["6"], "type": ["3"], "num": ["2"]},
            conn,
        )

    assert list(result.keys()) == ["data"]
    assert isinstance(result["data"], list)
    assert result["data"][0]["term"] == "12"


def test_legacy_result_keeps_expected_field_order_and_names(tmp_path: Path):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        result = handle_frontend_kaijiang_api(
            "/api/kaijiang/getJyxiao2",
            {"web": ["6"], "type": ["3"], "num": ["2"]},
            conn,
        )

    assert list(result["data"][0].keys()) == ["content", "res_code", "res_sx", "term", "xiao"]
