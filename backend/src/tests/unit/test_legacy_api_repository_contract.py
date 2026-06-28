from __future__ import annotations

from pathlib import Path

from db import connect
from legacy.api import get_legacy_current_term, list_legacy_post_images
from legacy.frontend_compat import handle_frontend_post_api


def _create_legacy_image_assets(conn) -> None:
    conn.execute(
        """
        CREATE TABLE legacy_image_assets (
            id INTEGER PRIMARY KEY,
            title TEXT,
            file_name TEXT,
            storage_path TEXT,
            legacy_upload_path TEXT,
            cover_image TEXT,
            mime_type TEXT,
            file_size INTEGER,
            sort_order INTEGER,
            enabled INTEGER,
            source_key TEXT,
            source_pc INTEGER,
            source_web INTEGER,
            source_type INTEGER
        )
        """
    )


def test_list_legacy_post_images_keeps_full_legacy_asset_shape(tmp_path: Path):
    db_path = tmp_path / "legacy_api_repository_contract.sqlite3"
    with connect(db_path) as conn:
        _create_legacy_image_assets(conn)
        conn.execute(
            """
            INSERT INTO legacy_image_assets (
                id, title, file_name, storage_path, legacy_upload_path, cover_image,
                mime_type, file_size, sort_order, enabled, source_key, source_pc, source_web, source_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                7,
                "card",
                "card.jpg",
                "data/images/card.jpg",
                "/upload/card.jpg",
                "/cover/card.jpg",
                "image/jpeg",
                1234,
                9,
                1,
                "legacy-post-list",
                305,
                4,
                3,
            ),
        )

    rows = list_legacy_post_images(
        db_path,
        source_pc=305,
        source_web=4,
        source_type=3,
        limit=20,
    )

    assert rows == [
        {
            "id": 7,
            "title": "card",
            "file_name": "card.jpg",
            "storage_path": "data/images/card.jpg",
            "legacy_upload_path": "/upload/card.jpg",
            "cover_image": "/cover/card.jpg",
            "mime_type": "image/jpeg",
            "file_size": 1234,
            "sort_order": 9,
            "enabled": 1,
        }
    ]


def test_frontend_post_get_list_keeps_data_wrapper_and_pc_72_fallback(tmp_path: Path):
    db_path = tmp_path / "legacy_frontend_repository_contract.sqlite3"
    with connect(db_path) as conn:
        _create_legacy_image_assets(conn)
        conn.execute(
            """
            INSERT INTO legacy_image_assets (
                id, title, cover_image, sort_order, enabled, source_key, source_pc, source_web, source_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (8, "fallback", "/cover/fallback.jpg", 2, 1, "legacy-post-list", 305, 4, 3),
        )

        result = handle_frontend_post_api(
            "/api/post/getList",
            {"pc": ["72"], "web": ["4"], "type": ["3"]},
            conn,
        )

    assert result == {
        "data": [
            {
                "id": 8,
                "title": "fallback",
                "cover_image": "/cover/fallback.jpg",
                "sort_order": 2,
            }
        ]
    }


def test_get_legacy_current_term_keeps_empty_fallback_shape(tmp_path: Path):
    db_path = tmp_path / "legacy_current_term_contract.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE lottery_draws (
                id INTEGER PRIMARY KEY,
                lottery_type_id INTEGER,
                year INTEGER,
                term INTEGER,
                next_term INTEGER,
                is_opened INTEGER
            )
            """
        )

    assert get_legacy_current_term(db_path, lottery_type_id=3) == {
        "lottery_type_id": 3,
        "term": "",
        "issue": "",
        "next_term": "",
    }
