from __future__ import annotations

from db import connect
from predict.mechanisms import build_title_prediction_configs


def test_jyxiao2_is_classified_as_content_xiao(tmp_path):
    db_path = str(tmp_path / "jyxiao2_config.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_tables (
                modes_id INTEGER PRIMARY KEY,
                table_name TEXT NOT NULL,
                title TEXT,
                record_count INTEGER
            )
            """
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
            "INSERT INTO mode_payload_tables (modes_id, table_name, title, record_count) VALUES (?, ?, ?, ?)",
            (251, "mode_payload_251", "title_251", 1),
        )
        conn.execute(
            """
            INSERT INTO mode_payload_251 (year, term, web, type, content, xiao, code, res_code, res_sx)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "2026",
                "1",
                6,
                3,
                '["鼠|05,17,29,41","牛|04,16,28,40","虎|03,15,27,39","兔|02,14,26,38"]',
                "",
                "01,02,03,04",
                "01,02,03,04,05,06,07",
                "龙,鸡,马,羊,狗,鼠,鼠",
            ),
        )
        conn.commit()

    config = build_title_prediction_configs(db_path)["title_251"]
    assert config.label_count == 4
    assert config.content_loader({"content": "", "xiao": "鼠,牛,虎,兔"}) == "鼠,牛,虎,兔"
    assert config.content_loader(
        {
            "content": '["鼠|05,17,29,41","牛|04,16,28,40","虎|03,15,27,39","兔|02,14,26,38"]',
            "xiao": "",
        }
    ) == "鼠,牛,虎,兔"
