from __future__ import annotations

from db import connect
from predict.mechanisms import random_text_pool_row


def test_random_text_pool_row_for_mode_52_is_postgres_group_by_safe(tmp_path):
    db_path = str(tmp_path / "mode_52_text_pool.sqlite3")

    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_52 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                jiexi TEXT,
                content TEXT,
                code TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO mode_payload_52 (title, jiexi, content, code)
            VALUES (?, ?, ?, ?)
            """,
            ("春风得意", "虎", "", ""),
        )
        conn.execute(
            """
            INSERT INTO mode_payload_52 (title, jiexi, content, code)
            VALUES (?, ?, ?, ?)
            """,
            ("春风得意", "虎", "", ""),
        )
        conn.execute(
            """
            INSERT INTO mode_payload_52 (title, jiexi, content, code)
            VALUES (?, ?, ?, ?)
            """,
            ("秋月无边", "龙", "", ""),
        )

        row = random_text_pool_row(conn, "四字玄机")

    assert row is not None
    assert row["title"] in {"春风得意", "秋月无边"}
    assert row["jiexi"] in {"虎", "龙"}
