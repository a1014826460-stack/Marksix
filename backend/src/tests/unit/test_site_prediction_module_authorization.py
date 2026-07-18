from __future__ import annotations

from db import connect
from legacy.api import load_legacy_mode_rows
from legacy.frontend_compat import handle_frontend_kaijiang_api
from vendor import homepage_modules
from domains.prediction.repository import (
    get_enabled_mode_ids_for_web_id,
    is_mode_enabled_for_web_id,
)


def _setup_authorization_tables(db_path: str) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE managed_sites (
                id INTEGER PRIMARY KEY,
                web_id INTEGER NOT NULL,
                name TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE site_prediction_modules (
                id INTEGER PRIMARY KEY,
                site_id INTEGER NOT NULL,
                mechanism_key TEXT NOT NULL,
                mode_id INTEGER NOT NULL,
                status INTEGER NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE lottery_draws (
                id INTEGER PRIMARY KEY,
                lottery_type_id INTEGER,
                year INTEGER,
                term INTEGER,
                numbers TEXT,
                is_opened INTEGER,
                next_term INTEGER,
                draw_time TEXT
            )
            """
        )
        conn.execute("INSERT INTO managed_sites (id, web_id, name) VALUES (7, 7, 'twjinniu')")
        conn.execute(
            """
            INSERT INTO site_prediction_modules (id, site_id, mechanism_key, mode_id, status)
            VALUES
                (1, 7, 'pt1xiao', 56, 1),
                (2, 7, 'disabled', 151, 0)
            """
        )


def test_enabled_mode_authorization_resolves_managed_site_by_web_id(tmp_path):
    db_path = str(tmp_path / "site_module_authorization.sqlite3")
    _setup_authorization_tables(db_path)

    with connect(db_path) as conn:
        assert get_enabled_mode_ids_for_web_id(conn, 7) == {56}
        assert is_mode_enabled_for_web_id(conn, web_id=7, mode_id=56) is True
        assert is_mode_enabled_for_web_id(conn, web_id=7, mode_id=151) is False
        assert is_mode_enabled_for_web_id(conn, web_id=999, mode_id=56) is False


def test_vendor_composite_keeps_empty_history_when_a_source_mode_is_disabled(monkeypatch):
    monkeypatch.setattr(
        homepage_modules,
        "resolve_public_site",
        lambda *_args, **_kwargs: {"id": 5, "web_id": 5, "lottery_type_id": 3},
    )
    monkeypatch.setattr(
        homepage_modules,
        "load_legacy_mode_rows",
        lambda *_args, **_kwargs: {
            "rows": [
                {
                    "year": "2026",
                    "term": "1",
                    "content": '["鼠|01"]',
                    "draw_is_opened": False,
                }
            ]
        },
    )
    monkeypatch.setattr(
        homepage_modules,
        "get_enabled_mode_ids_for_web_id",
        lambda _conn, _web_id: {47, 69},
    )

    payload = homepage_modules.build_vendor_homepage_modules(
        "unused",
        site_id=5,
        lottery_type=3,
        module_keys=["wuxiao_wuma"],
    )

    assert payload["data"] == [
        {
            "module_key": "wuxiao_wuma",
            "title": "五肖五码",
            "display_style": "table-composite",
            "history": [],
        }
    ]


def test_legacy_module_rows_keep_metadata_and_empty_rows_when_mode_is_disabled(tmp_path):
    db_path = str(tmp_path / "legacy_module_authorization.sqlite3")
    _setup_authorization_tables(db_path)

    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_tables (
                modes_id INTEGER PRIMARY KEY,
                title TEXT,
                table_name TEXT NOT NULL,
                record_count INTEGER
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE mode_payload_151 (
                year TEXT, term TEXT, web INTEGER, type INTEGER, content TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO mode_payload_tables (modes_id, title, table_name, record_count)
            VALUES (151, 'disabled', 'mode_payload_151', 1)
            """
        )
        conn.execute(
            """
            INSERT INTO mode_payload_151 (year, term, web, type, content)
            VALUES ('2026', '1', 7, 3, 'should not be exposed')
            """
        )

    payload = load_legacy_mode_rows(
        db_path,
        modes_id=151,
        web=7,
        type_value=3,
    )

    assert payload == {
        "modes_id": 151,
        "title": "disabled",
        "table_name": "mode_payload_151",
        "record_count": 1,
        "rows": [],
    }


def test_legacy_kaijiang_keeps_data_wrapper_when_explicit_web_has_disabled_mode(tmp_path):
    db_path = str(tmp_path / "legacy_kaijiang_authorization.sqlite3")
    _setup_authorization_tables(db_path)

    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_151 (
                year TEXT, term TEXT, web INTEGER, type INTEGER,
                content TEXT, xiao TEXT, code TEXT, res_code TEXT, res_sx TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO mode_payload_151 (
                year, term, web, type, content, xiao, code, res_code, res_sx
            ) VALUES ('2026', '1', 7, 3, 'visible without authorization', '', '', '', '')
            """
        )

        payload = handle_frontend_kaijiang_api(
            "/api/kaijiang/getXysxma",
            {"web": ["7"], "type": ["3"], "num": ["9/8"]},
            conn,
        )

    assert payload == {"data": []}
