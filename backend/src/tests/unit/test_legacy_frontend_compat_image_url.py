from __future__ import annotations

import sys
from pathlib import Path

from db import connect
from legacy.frontend_compat import handle_frontend_kaijiang_api


_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def test_get_pmxjcz_returns_image_url_field(tmp_path: Path):
    db_path = str(tmp_path / "legacy_frontend_compat_image_url.sqlite3")
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
            (475, "mode_payload_475"),
        )
        conn.execute(
            """
            CREATE TABLE mode_payload_475 (
                year TEXT,
                term TEXT,
                web INTEGER,
                type INTEGER,
                title TEXT,
                content TEXT,
                image_url TEXT,
                res_code TEXT,
                res_sx TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO mode_payload_475 (
                year, term, web, type, title, content, image_url, res_code, res_sx
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "2026",
                "139",
                4,
                3,
                "脑筋急转弯",
                "2026139期不长叶的树是哪棵？",
                "/data/Images/mode_475/prediction/brain_teaser_2026139_web4.jpg",
                "",
                "",
            ),
        )
        conn.commit()

    with connect(db_path) as conn:
        result = handle_frontend_kaijiang_api(
            "/api/kaijiang/getPmxjcz",
            {"web": ["4"], "type": ["3"], "num": ["475"]},
            conn,
        )

    assert result["data"] == [
        {
            "year": "2026",
            "term": "139",
            "title": "脑筋急转弯",
            "content": "2026139期不长叶的树是哪棵？",
            "image_url": "/data/Images/mode_475/prediction/brain_teaser_2026139_web4.jpg",
            "x7m14": result["data"][0]["x7m14"],
            "res_code": "",
            "res_sx": "",
        }
    ]
