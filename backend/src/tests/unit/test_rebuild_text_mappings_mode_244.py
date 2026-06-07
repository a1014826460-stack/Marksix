from __future__ import annotations

from db import connect
from database.yiyupotianji_seed_rows import YIYUPOTIANJI_TEXT_POOL_CONTENTS
from utils.rebuild_text_mappings import rebuild_text_history_mappings


def test_rebuild_text_history_mappings_includes_mode_244_source_and_seed_pool(tmp_path):
    db_path = str(tmp_path / "mode_244_text_pool.sqlite3")

    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_tables (
                modes_id INTEGER,
                title TEXT,
                table_name TEXT,
                record_count INTEGER,
                is_text INTEGER
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE mode_payload_244 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year TEXT,
                term TEXT,
                content TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO mode_payload_tables (modes_id, title, table_name, record_count, is_text)
            VALUES (50, '一字真言', 'mode_payload_50', 0, 1)
            """
        )
        conn.execute(
            """
            CREATE TABLE mode_payload_50 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                jiexi TEXT,
                title TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO mode_payload_244 (year, term, content)
            VALUES
                ('2026', '001', '四海为家无定踪，浪迹天涯卖艺人'),
                ('2026', '002', '四海为家无定踪，浪迹天涯卖艺人'),
                ('2026', '003', '黑夜冬季微风凉，初夏一到细雨香')
            """
        )
        conn.commit()

    result = rebuild_text_history_mappings(db_path)

    with connect(db_path) as conn:
        total_244 = int(
            conn.execute(
                "SELECT COUNT(*) AS total FROM text_history_mappings WHERE mode_id = ?",
                (244,),
            ).fetchone()["total"]
            or 0
        )
        distinct_source = int(
            conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM text_history_mappings
                WHERE mode_id = ?
                  AND content IN (?, ?)
                """,
                (
                    244,
                    "四海为家无定踪，浪迹天涯卖艺人",
                    "黑夜冬季微风凉，初夏一到细雨香",
                ),
            ).fetchone()["total"]
            or 0
        )

    assert result["mode_244_inserted"] == len(YIYUPOTIANJI_TEXT_POOL_CONTENTS) + 2
    assert total_244 == len(YIYUPOTIANJI_TEXT_POOL_CONTENTS) + 2
    assert distinct_source == 2
