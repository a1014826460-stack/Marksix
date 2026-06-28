from __future__ import annotations

import pytest

from core.errors import ForbiddenError, NotFoundError
from db import connect
from domains.prediction import mode_payload_service


def test_mode_payload_row_ownership_allows_matching_web_id_column(tmp_path):
    db_path = tmp_path / "mode_payload_owner.sqlite3"
    with connect(db_path) as conn:
        conn.execute("CREATE TABLE mode_payload_43 (id INTEGER PRIMARY KEY, web_id INTEGER, content TEXT)")
        conn.execute("INSERT INTO mode_payload_43 (id, web_id, content) VALUES (12, 6, 'ok')")

    mode_payload_service.ensure_mode_payload_row_belongs_to_site(
        db_path,
        "mode_payload_43",
        "12",
        site_web_id=6,
    )


def test_mode_payload_row_ownership_allows_legacy_web_column(tmp_path):
    db_path = tmp_path / "mode_payload_owner_web.sqlite3"
    with connect(db_path) as conn:
        conn.execute("CREATE TABLE mode_payload_44 (id INTEGER PRIMARY KEY, web INTEGER, content TEXT)")
        conn.execute("INSERT INTO mode_payload_44 (id, web, content) VALUES (12, 6, 'ok')")

    mode_payload_service.ensure_mode_payload_row_belongs_to_site(
        db_path,
        "mode_payload_44",
        12,
        site_web_id=6,
    )


def test_mode_payload_row_ownership_allows_tables_without_web_columns(tmp_path):
    db_path = tmp_path / "mode_payload_owner_no_web.sqlite3"
    with connect(db_path) as conn:
        conn.execute("CREATE TABLE mode_payload_45 (id INTEGER PRIMARY KEY, content TEXT)")
        conn.execute("INSERT INTO mode_payload_45 (id, content) VALUES (12, 'ok')")

    mode_payload_service.ensure_mode_payload_row_belongs_to_site(
        db_path,
        "mode_payload_45",
        12,
        site_web_id=6,
    )


def test_mode_payload_row_ownership_rejects_cross_site_rows(tmp_path):
    db_path = tmp_path / "mode_payload_owner_forbidden.sqlite3"
    with connect(db_path) as conn:
        conn.execute("CREATE TABLE mode_payload_46 (id INTEGER PRIMARY KEY, web_id INTEGER, web INTEGER)")
        conn.execute("INSERT INTO mode_payload_46 (id, web_id, web) VALUES (12, 7, 8)")

    with pytest.raises(ForbiddenError):
        mode_payload_service.ensure_mode_payload_row_belongs_to_site(
            db_path,
            "mode_payload_46",
            12,
            site_web_id=6,
        )


def test_mode_payload_row_ownership_raises_not_found_for_missing_row(tmp_path):
    db_path = tmp_path / "mode_payload_owner_missing.sqlite3"
    with connect(db_path) as conn:
        conn.execute("CREATE TABLE mode_payload_47 (id INTEGER PRIMARY KEY, web_id INTEGER)")

    with pytest.raises(NotFoundError):
        mode_payload_service.ensure_mode_payload_row_belongs_to_site(
            db_path,
            "mode_payload_47",
            12,
            site_web_id=6,
        )


def test_list_mode_payload_rows_filters_sorts_and_paginates_public_rows(tmp_path):
    db_path = tmp_path / "mode_payload_list.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_48 (
                id INTEGER PRIMARY KEY,
                year INTEGER,
                term INTEGER,
                type INTEGER,
                web_id INTEGER,
                content TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO mode_payload_48 (id, year, term, type, web_id, content, created_at)
            VALUES
                (1, 2026, 130, 3, 6, 'alpha old', '2026-06-27T00:00:00Z'),
                (2, 2026, 132, 3, 6, 'alpha newest', '2026-06-27T00:02:00Z'),
                (3, 2026, 131, 3, 7, 'alpha other site', '2026-06-27T00:01:00Z'),
                (4, 2026, 129, 2, 6, 'alpha wrong type', '2026-06-27T00:03:00Z')
            """
        )

    payload = mode_payload_service.list_mode_payload_rows(
        db_path,
        "mode_payload_48",
        type_filter="3",
        web_filter="6",
        page=1,
        page_size=1,
        search="alpha",
        source="public",
    )

    assert payload == {
        "rows": [
            {
                "id": 2,
                "year": 2026,
                "term": 132,
                "type": 3,
                "web_id": 6,
                "content": "alpha newest",
                "created_at": "2026-06-27T00:02:00Z",
            }
        ],
        "total": 2,
        "page": 1,
        "page_size": 1,
        "columns": ["id", "year", "term", "type", "web_id", "content", "created_at"],
    }


def test_update_mode_payload_row_updates_editable_columns_and_preserves_response_shape(tmp_path):
    db_path = tmp_path / "mode_payload_update.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_49 (
                id INTEGER PRIMARY KEY,
                web_id INTEGER,
                table_modes_id INTEGER,
                content TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO mode_payload_49 (id, web_id, table_modes_id, content)
            VALUES (12, 6, 43, 'old')
            """
        )

    payload = mode_payload_service.update_mode_payload_row(
        db_path,
        "mode_payload_49",
        "12",
        {
            "id": 99,
            "web_id": 7,
            "table_modes_id": 88,
            "content": "updated",
            "data_source": "created",
            "missing": "ignored",
        },
    )

    assert payload == {
        "row": {
            "id": 12,
            "web_id": 7,
            "table_modes_id": 43,
            "content": "updated",
        }
    }


def test_delete_mode_payload_row_removes_row_without_response_payload(tmp_path):
    db_path = tmp_path / "mode_payload_delete.sqlite3"
    with connect(db_path) as conn:
        conn.execute("CREATE TABLE mode_payload_50 (id INTEGER PRIMARY KEY, content TEXT)")
        conn.execute("INSERT INTO mode_payload_50 (id, content) VALUES (12, 'old')")

    result = mode_payload_service.delete_mode_payload_row(
        db_path,
        "mode_payload_50",
        "12",
    )

    assert result is None
    with connect(db_path) as conn:
        assert conn.execute("SELECT id FROM mode_payload_50 WHERE id = 12").fetchone() is None
