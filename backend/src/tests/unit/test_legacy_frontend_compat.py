from __future__ import annotations

import sys
from pathlib import Path

from db import connect
from legacy.frontend_compat import handle_frontend_kaijiang_api


_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _setup_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "legacy_frontend_compat.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_tables (
                modes_id INTEGER PRIMARY KEY,
                table_name TEXT NOT NULL
            )
            """
        )

        for modes_id, table_name in (
            (24, "mode_payload_24"),
            (151, "mode_payload_151"),
            (251, "mode_payload_251"),
        ):
            conn.execute(
                "INSERT INTO mode_payload_tables (modes_id, table_name) VALUES (?, ?)",
                (modes_id, table_name),
            )
            conn.execute(
                f"""
                CREATE TABLE {table_name} (
                    year TEXT,
                    term TEXT,
                    web INTEGER,
                    type INTEGER,
                    content TEXT,
                    xiao TEXT,
                    code TEXT,
                    nan TEXT,
                    nv TEXT,
                    zi TEXT,
                    jiexi TEXT,
                    res_code TEXT,
                    res_sx TEXT
                )
                """
            )

        for term in range(1, 13):
            conn.execute(
                """
                INSERT INTO mode_payload_251 (
                    year, term, web, type, content, xiao, code, res_code, res_sx
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "2026",
                    str(term),
                    6,
                    3,
                    '["鼠|05,17,29,41","牛|04,16,28,40"]',
                    "鼠,牛,虎,兔",
                    "01,02,03,04",
                    "01,02,03,04,05,06,07",
                    "龙,鸡,马,羊,狗,鼠,鼠",
                ),
            )

        conn.execute(
            """
            INSERT INTO mode_payload_24 (
                year, term, web, type, content, nan, nv, res_code, res_sx
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("2026", "99", 6, 3, '{"nan":"鼠,牛,虎,兔","nv":"鼠,牛,虎,兔"}', "", "", "01,02,03,04,05,06,07", ""),
        )

        conn.execute(
            """
            INSERT INTO mode_payload_151 (
                year, term, web, type, content, xiao, code, res_code, res_sx
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("2026", "88", 6, 3, '["羊|46,34,47,23,27,03,02,38"]', "", "", None, "鼠,牛,虎,兔"),
        )

        conn.commit()

    return db_path


def test_standard_kaijiang_caps_rows_to_10_and_uses_endpoint_mapping(tmp_path: Path):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        result = handle_frontend_kaijiang_api(
            "/api/kaijiang/getJyxiao2",
            {"web": ["6"], "type": ["3"], "num": ["2"]},
            conn,
        )

    data = result["data"]
    assert len(data) == 10
    assert data[0]["term"] == "12"
    assert data[-1]["term"] == "3"
    assert list(data[0].keys()) == ["content", "res_code", "res_sx", "term", "xiao"]
    assert data[0]["content"].startswith("[")
    assert data[0]["content"] != "[]"
    assert data[0]["xiao"] == "鼠,牛,虎,兔"
    assert "鼠|" in data[0]["content"]


def test_standard_kaijiang_returns_string_fields_and_empty_result_fields(tmp_path: Path):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        result = handle_frontend_kaijiang_api(
            "/api/kaijiang/getNnnx",
            {"web": ["6"], "type": ["3"], "num": ["4"]},
            conn,
        )

    assert result["data"] == [
        {
            "nan": "鼠,牛,虎,兔",
            "nv": "鼠,牛,虎,兔",
            "res_code": "01,02,03,04,05,06,07",
            "res_sx": "",
            "term": "99",
        }
    ]
    assert all(isinstance(value, str) for value in result["data"][0].values())


def test_standard_kaijiang_supports_get_xysxma_contract(tmp_path: Path):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        result = handle_frontend_kaijiang_api(
            "/api/kaijiang/getXysxma",
            {"web": ["6"], "type": ["3"], "num": ["9/8"]},
            conn,
        )

    assert result["data"] == [
        {
            "code": "46,34,47,23,27,03,02,38",
            "res_code": "",
            "res_sx": "鼠,牛,虎,兔",
            "term": "88",
            "xiao": "羊",
        }
    ]
