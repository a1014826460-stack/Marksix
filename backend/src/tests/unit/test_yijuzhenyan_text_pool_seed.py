from __future__ import annotations

from db import connect
from database.seed import seed_yijuzhenyan_text_pool
from database.yijuzhenyan_seed_rows import YIJUZHENYAN_TEXT_POOL_ROWS


def test_seed_yijuzhenyan_text_pool_is_idempotent_and_syncs_mappings(tmp_path):
    db_path = str(tmp_path / "yijuzhenyan_seed.sqlite3")

    with connect(db_path) as conn:
        first = seed_yijuzhenyan_text_pool(conn, now="2026-06-04T00:00:00+00:00")
        second = seed_yijuzhenyan_text_pool(conn, now="2026-06-04T00:00:00+00:00")

        source_count = int(
            conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM mode_payload_50
                WHERE web = ? AND type = ? AND year = ?
                """,
                ("seed_pool", "yijuzhenyan", "0"),
            ).fetchone()["total"]
            or 0
        )
        mapping_count = int(
            conn.execute(
                "SELECT COUNT(*) AS total FROM text_history_mappings WHERE mode_id = ?",
                (50,),
            ).fetchone()["total"]
            or 0
        )

    assert first["inserted"] == len(YIJUZHENYAN_TEXT_POOL_ROWS)
    assert first["updated"] == 0
    assert first["rebuilt_mappings"] is True
    assert second["inserted"] == 0
    assert second["updated"] == 0
    assert second["rebuilt_mappings"] is False
    assert source_count == len(YIJUZHENYAN_TEXT_POOL_ROWS)
    assert mapping_count == len(YIJUZHENYAN_TEXT_POOL_ROWS)
