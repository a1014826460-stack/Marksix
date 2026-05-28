from __future__ import annotations

from db import connect
from tables import ensure_admin_tables
from domains.prediction.generation_service import (
    get_site_prediction_modules_from_db_or_blueprint,
    sync_site_prediction_modules,
)
from predict.mechanisms import ensure_prediction_configs_loaded


def _setup_db(db_path: str) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE managed_sites (
                id INTEGER PRIMARY KEY,
                name TEXT,
                domain TEXT,
                lottery_type_id INTEGER,
                web_id INTEGER,
                start_web_id INTEGER,
                end_web_id INTEGER
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE site_prediction_modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER NOT NULL,
                mechanism_key TEXT NOT NULL,
                status INTEGER NOT NULL,
                sort_order INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                mode_id INTEGER,
                title TEXT,
                UNIQUE(site_id, mechanism_key)
            )
            """
        )


def test_existing_site_modules_are_database_source_of_truth(tmp_path):
    db_path = str(tmp_path / "site_modules.sqlite3")
    _setup_db(db_path)

    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO managed_sites (
                id, name, domain, lottery_type_id, web_id, start_web_id, end_web_id
            ) VALUES (5, 'twcaibawang', 'www.twcaibawang.com', 3, 5, 5, 5)
            """
        )
        conn.execute(
            """
            INSERT INTO site_prediction_modules (
                site_id, mechanism_key, status, sort_order, created_at, updated_at, mode_id, title
            ) VALUES (5, '3tou', 1, 999, 'now', 'now', 12, 'custom')
            """
        )

        site = dict(conn.execute("SELECT * FROM managed_sites WHERE id = 5").fetchone())
        before = get_site_prediction_modules_from_db_or_blueprint(conn, site)
        sync_site_prediction_modules(conn, site_id=5)
        rows = conn.execute(
            "SELECT mechanism_key, sort_order FROM site_prediction_modules WHERE site_id = 5"
        ).fetchall()

    assert [item["key"] for item in before] == ["3tou"]
    assert [(row["mechanism_key"], row["sort_order"]) for row in rows] == [("3tou", 999)]


def test_empty_site_modules_can_be_initialized_from_blueprint(tmp_path):
    db_path = str(tmp_path / "site_modules_empty.sqlite3")
    _setup_db(db_path)

    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO managed_sites (
                id, name, domain, lottery_type_id, web_id, start_web_id, end_web_id
            ) VALUES (8, 'new', '', 3, 8, 8, 8)
            """
        )

        sync_site_prediction_modules(conn, site_id=8)
        count = conn.execute(
            "SELECT COUNT(*) AS total FROM site_prediction_modules WHERE site_id = 8"
        ).fetchone()["total"]

    assert count > 0


def test_dynamic_title_module_rows_are_resolved_from_database_configs(tmp_path):
    db_path = str(tmp_path / "site_modules_dynamic.sqlite3")
    _setup_db(db_path)

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
            """
            INSERT INTO mode_payload_tables (modes_id, table_name, title, record_count)
            VALUES (251, 'mode_payload_251', '家野两肖', 1)
            """
        )
        conn.execute(
            """
            INSERT INTO mode_payload_251 (year, term, web, type, content, xiao, code, res_code, res_sx)
            VALUES (
                '2026', '1', 6, 3,
                '["鼠|05,17,29,41","牛|04,16,28,40","虎|03,15,27,39","兔|02,14,26,38"]',
                '',
                '01,02,03,04',
                '01,02,03,04,05,06,07',
                '龙,鸡,马,羊,狗,鼠,牛'
            )
            """
        )
        conn.execute(
            """
            INSERT INTO managed_sites (
                id, name, domain, lottery_type_id, web_id, start_web_id, end_web_id
            ) VALUES (6, 'twsaimahui', 'www.twsaimahui.com', 3, 6, 6, 6)
            """
        )
        conn.execute(
            """
            INSERT INTO site_prediction_modules (
                site_id, mechanism_key, status, sort_order, created_at, updated_at, mode_id, title
            ) VALUES (6, 'title_251', 1, 10, 'now', 'now', 251, '家野两肖')
            """
        )
        conn.commit()

        ensure_prediction_configs_loaded(db_path)
        site = dict(conn.execute("SELECT * FROM managed_sites WHERE id = 6").fetchone())
        modules = get_site_prediction_modules_from_db_or_blueprint(conn, site)

    assert [item["key"] for item in modules] == ["title_251"]
    assert modules[0]["blueprint_name"] == "database"
    assert int(modules[0]["mode_id"]) == 251


def test_bootstrap_seeds_site_blueprint_profiles_and_site_assignment(tmp_path):
    db_path = str(tmp_path / "site_blueprints.sqlite3")
    ensure_admin_tables(db_path)

    with connect(db_path) as conn:
        managed_site_columns = set(conn.table_columns("managed_sites"))
        profile_count = conn.execute(
            "SELECT COUNT(*) AS total FROM site_blueprint_profiles"
        ).fetchone()["total"]

        conn.execute(
            """
            INSERT INTO managed_sites (
                id, web_id, name, domain, lottery_type_id, enabled, start_web_id, end_web_id,
                manage_url_template, modes_data_url, token, blueprint_name, request_limit,
                request_delay, announcement, notes, created_at, updated_at
            )
            VALUES (
                5, 5, '台湾彩霸王', 'www.twcaibawang.com', 3, 1, 5, 5,
                'https://example.com/{web_id}', 'https://example.com/api', '',
                'twcaibawang', 250, 0.5, '', '', 'now', 'now'
            )
            ON CONFLICT(id) DO UPDATE SET blueprint_name = excluded.blueprint_name
            """
        )
        site = conn.execute(
            """
            SELECT s.*, bp.required_mode_ids_json AS blueprint_required_mode_ids_json
            FROM managed_sites s
            LEFT JOIN site_blueprint_profiles bp ON bp.blueprint_name = s.blueprint_name
            WHERE s.id = 5
            """
        ).fetchone()

    assert "blueprint_name" in managed_site_columns
    assert int(profile_count) >= 3
    assert site["blueprint_name"] == "twcaibawang"
    assert str(site["blueprint_required_mode_ids_json"] or "").startswith("[")
