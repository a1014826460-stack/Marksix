from __future__ import annotations

from db import connect
from domains.legacy import repository


def test_legacy_repository_lists_post_images_with_legacy_fallback_pc(tmp_path):
    db_path = tmp_path / "legacy_repository.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE legacy_image_assets (
                id INTEGER PRIMARY KEY,
                title TEXT,
                cover_image TEXT,
                sort_order INTEGER,
                enabled INTEGER,
                source_key TEXT,
                source_pc INTEGER,
                source_web INTEGER,
                source_type INTEGER
            )
            """
        )
        conn.execute(
            """
            INSERT INTO legacy_image_assets (
                id, title, cover_image, sort_order, enabled, source_key, source_pc, source_web, source_type
            ) VALUES
                (1, 'fallback', '/a.jpg', 2, 1, 'legacy-post-list', 305, 4, 3),
                (2, 'disabled', '/b.jpg', 1, 0, 'legacy-post-list', 305, 4, 3)
            """
        )

        rows = repository.list_frontend_post_images(
            conn,
            pc=72,
            web_id=4,
            type_value=3,
        )

    assert rows == [{"id": 1, "title": "fallback", "cover_image": "/a.jpg", "sort_order": 2}]


def test_legacy_repository_resolves_current_term_from_lottery_draws(tmp_path):
    db_path = tmp_path / "legacy_current_term.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE lottery_draws (
                id INTEGER PRIMARY KEY,
                lottery_type_id INTEGER,
                year INTEGER,
                term INTEGER,
                next_term INTEGER,
                numbers TEXT,
                is_opened INTEGER
            )
            """
        )
        conn.execute(
            """
            INSERT INTO lottery_draws (lottery_type_id, year, term, next_term, numbers, is_opened)
            VALUES (3, 2026, 130, 131, '01,02,03,04,05,06,07', 1)
            """
        )

        payload = repository.get_latest_opened_term(conn, lottery_type_id=3)

    assert payload == {
        "lottery_type_id": 3,
        "term": "130",
        "issue": "2026130",
        "next_term": "131",
    }


def test_legacy_repository_gets_mode_payload_metadata(tmp_path):
    db_path = tmp_path / "legacy_mode_payload_metadata.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_tables (
                modes_id INTEGER PRIMARY KEY,
                title TEXT,
                table_name TEXT NOT NULL,
                record_count INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            INSERT INTO mode_payload_tables (modes_id, title, table_name, record_count)
            VALUES (?, ?, ?, ?)
            """,
            (152, "ZYX", "mode_payload_152", 12),
        )

        meta = repository.get_mode_payload_metadata(conn, modes_id=152)
        missing = repository.get_mode_payload_metadata(conn, modes_id=999)

    assert meta == {
        "modes_id": 152,
        "title": "ZYX",
        "table_name": "mode_payload_152",
        "record_count": 12,
    }
    assert missing is None
