"""四字玄机（mode 52）备选池：49 组 (title, jiexi) 必须可重建、幂等且配对。"""

from __future__ import annotations

from db import connect
from utils.rebuild_text_mappings import (
    MODE_52_ID,
    MODE_52_SIZIXUANJI_POOL,
    insert_mode_52_sizixuanji_pool,
    rebuild_text_history_mappings,
)


def _create_mapping_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE text_history_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mode_id INTEGER NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            jiexi TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX idx_text_history_unique
        ON text_history_mappings (mode_id, content, jiexi, title)
        """
    )
    conn.commit()


def test_mode_52_pool_has_49_distinct_pairs():
    assert len(MODE_52_SIZIXUANJI_POOL) == 49
    titles = [title for title, _jiexi in MODE_52_SIZIXUANJI_POOL]
    jiexi_values = [jiexi for _title, jiexi in MODE_52_SIZIXUANJI_POOL]
    assert len(set(titles)) == 49, "标题必须互不重复"
    assert len(set(jiexi_values)) == 49, "解肖组合必须互不重复"
    for title, jiexi in MODE_52_SIZIXUANJI_POOL:
        assert len(title) == 4, f"{title} 不是四字标题"
        assert len(jiexi) == 7, f"{jiexi} 不是 7 肖解肖"
        assert len(set(jiexi)) == 7, f"{jiexi} 有重复生肖"


def test_mode_52_backfill_is_idempotent(tmp_path):
    db_path = str(tmp_path / "mode_52_pool.sqlite3")

    with connect(db_path) as conn:
        _create_mapping_table(conn)
        first = insert_mode_52_sizixuanji_pool(conn)
        second = insert_mode_52_sizixuanji_pool(conn)
        total = int(
            conn.execute(
                "SELECT COUNT(*) AS total FROM text_history_mappings WHERE mode_id = ?",
                (MODE_52_ID,),
            ).fetchone()["total"]
            or 0
        )
        paired = int(
            conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM text_history_mappings
                WHERE mode_id = ? AND title <> '' AND jiexi <> ''
                """,
                (MODE_52_ID,),
            ).fetchone()["total"]
            or 0
        )

    assert first == 49
    assert second == 0
    assert total == 49
    assert paired == 49, "title 与 jiexi 必须成对写入"


def test_full_rebuild_keeps_mode_52_pool(tmp_path):
    """mode_payload_52 未标记 is_text=1，重建后仍必须带上 49 组候选。"""
    db_path = str(tmp_path / "mode_52_rebuild.sqlite3")

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
            INSERT INTO mode_payload_tables (modes_id, title, table_name, record_count, is_text)
            VALUES (52, '四字玄机', 'mode_payload_52', 0, 0)
            """
        )
        conn.commit()

    result = rebuild_text_history_mappings(db_path)

    with connect(db_path) as conn:
        total = int(
            conn.execute(
                "SELECT COUNT(*) AS total FROM text_history_mappings WHERE mode_id = ?",
                (MODE_52_ID,),
            ).fetchone()["total"]
            or 0
        )

    assert result["mode_52_inserted"] == 49
    assert total == 49
    assert result["inserted"] >= 49


def test_backfill_requires_existing_mapping_table(tmp_path):
    db_path = str(tmp_path / "mode_52_missing.sqlite3")

    with connect(db_path) as conn:
        try:
            insert_mode_52_sizixuanji_pool(conn)
        except ValueError as exc:
            assert "text_history_mappings" in str(exc)
        else:  # pragma: no cover - 必须抛错
            raise AssertionError("缺少映射表时应显式报错，而不是静默跳过")
