from __future__ import annotations

import json
from pathlib import Path

import pytest

from db import connect
from database.schema.prediction import _backfill_site_blueprint_names
from domains.prediction.site_module_audit import (
    audit_runtime_module_sets,
    audit_frontend_fixed_mode_dependencies,
    parse_shengshi8800_document_mode_ids,
    parse_twsaimahui_document_mode_ids,
    parse_twcf888_document_mode_ids,
    parse_twjinniu_homepage_mode_ids,
    reconcile_site_prediction_modules_to_blueprint,
)
from domains.prediction.site_module_blueprints import TWJINNIU_REQUIRED_MODE_IDS
from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key
from vendor.homepage_modules import get_vendor_module_source_mode_ids


@pytest.mark.parametrize(
    "site_key, web_id",
    (
        ("shengshi8800", 4),
        ("twcaibawang", 5),
        ("twsaimahui", 6),
        ("twjinniu", 7),
        ("twcf888", 8),
        ("twssz", 9),
        ("twbst528", 10),
    ),
)
def test_site_blueprint_equals_manifest_required_modes(site_key, web_id):
    from domains.prediction.site_module_blueprints import get_required_mode_ids_for_site
    from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key

    assert set(get_required_mode_ids_for_site({"web_id": web_id})) == set(
        required_mode_ids_for_site_key(site_key)
    )


@pytest.mark.parametrize(
    "site_key, constant_name",
    (
        ("twcaibawang", "TWCAIBAWANG_REQUIRED_MODE_IDS"),
        ("twsaimahui", "TWSAIMAHUI_REQUIRED_MODE_IDS"),
        ("twjinniu", "TWJINNIU_REQUIRED_MODE_IDS"),
        ("twcf888", "TWCF888_REQUIRED_MODE_IDS"),
    ),
)
def test_legacy_blueprint_constants_are_derived_from_the_page_manifest(site_key, constant_name):
    """Compatibility exports must never become a second authorization source."""
    from database.schema import prediction as schema_prediction
    from domains.prediction import site_module_blueprints

    expected = required_mode_ids_for_site_key(site_key)
    assert getattr(schema_prediction, constant_name) == expected
    assert getattr(site_module_blueprints, constant_name) == expected


def test_reconcile_site_four_disables_active_mode_absent_from_manifest(tmp_path):
    db_path = str(tmp_path / "shengshi8800_manifest_authorization.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE managed_sites (
                id INTEGER PRIMARY KEY,
                web_id INTEGER NOT NULL,
                domain TEXT,
                lottery_type_id INTEGER,
                blueprint_name TEXT
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
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                title TEXT,
                UNIQUE(site_id, mechanism_key)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO managed_sites (id, web_id, domain, lottery_type_id, blueprint_name)
            VALUES (4, 4, 'www.tw8800.com', 3, 'shengshi8800')
            """
        )
        conn.execute(
            """
            INSERT INTO site_prediction_modules (id, site_id, mechanism_key, mode_id, status)
            VALUES
                (1, 4, 'pmxjcz', 331, 1),
                (2, 4, 'legacy_64', 64, 1)
            """
        )

        reconcile_site_prediction_modules_to_blueprint(conn, site_ids=[4])
        rows = conn.execute(
            """
            SELECT mode_id, status
            FROM site_prediction_modules
            WHERE site_id = 4 AND mode_id IN (64, 331)
            ORDER BY mode_id
            """
        ).fetchall()

    assert [(int(row["mode_id"]), int(row["status"])) for row in rows] == [
        (64, 0),
        (331, 1),
    ]


def _setup_audit_tables(db_path: str) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE managed_sites (
                id INTEGER PRIMARY KEY,
                web_id INTEGER NOT NULL,
                domain TEXT,
                lottery_type_id INTEGER,
                blueprint_name TEXT,
                enabled INTEGER DEFAULT 1
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
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                title TEXT,
                UNIQUE(site_id, mechanism_key)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO managed_sites (id, web_id, domain, lottery_type_id, blueprint_name)
            VALUES (8, 8, 'www.twcf888.com', 3, 'twcf888')
            """
        )
        conn.execute(
            """
            INSERT INTO site_prediction_modules (id, site_id, mechanism_key, mode_id, status)
            VALUES
                (1, 8, 'tail6', 2, 1),
                (2, 8, 'legacy-extra', 44, 1),
                (3, 8, 'disabled-required', 5, 0)
            """
        )


def test_runtime_audit_reports_missing_disabled_and_extra_mode_ids(tmp_path):
    db_path = str(tmp_path / "site_module_audit.sqlite3")
    _setup_audit_tables(db_path)

    with connect(db_path) as conn:
        audit = audit_runtime_module_sets(conn, site_ids=[8])

    report = audit[0]
    expected_mode_ids = list(required_mode_ids_for_site_key("twcf888"))
    assert report["site_id"] == 8
    assert report["web_id"] == 8
    assert report["blueprint_name"] == "twcf888"
    assert report["blueprint_mode_ids"] == expected_mode_ids
    assert report["manifest_mode_ids"] == expected_mode_ids
    assert report["enabled_mode_ids"] == [2, 44]
    assert report["missing_from_runtime"] == [
        mode_id for mode_id in expected_mode_ids if mode_id != 2
    ]
    assert report["enabled_outside_blueprint"] == [44]
    assert report["vendor_dependency_mode_ids"] == []
    assert report["enabled_outside_authorized_sources"] == [44]
    assert report["blocked_dependency_sources"] == [
        "frontend/lib/twcf888-articles.ts"
    ]


def test_runtime_audit_resolves_web_ten_to_the_twbst528_manifest(tmp_path):
    db_path = str(tmp_path / "twbst528_site_module_audit.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE managed_sites (
                id INTEGER PRIMARY KEY,
                web_id INTEGER NOT NULL,
                domain TEXT,
                lottery_type_id INTEGER,
                blueprint_name TEXT
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
                status INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO managed_sites (id, web_id, domain, lottery_type_id, blueprint_name) VALUES (10, 10, 'www.twbst528.com', 3, 'twbst528')"
        )
        conn.execute(
            "INSERT INTO site_prediction_modules (id, site_id, mechanism_key, mode_id, status) VALUES (1, 10, 'yijuzhenyan', 50, 1)"
        )

        report = audit_runtime_module_sets(conn, site_ids=[10])[0]

    expected = list(required_mode_ids_for_site_key("twbst528"))
    assert report["site_id"] == 10
    assert report["web_id"] == 10
    assert report["blueprint_name"] == "twbst528"
    assert report["manifest_mode_ids"] == expected
    assert report["enabled_mode_ids"] == [50]
    assert report["missing_from_runtime"] == [mode_id for mode_id in expected if mode_id != 50]


def test_reconcile_disables_active_mode_absent_from_manifest(tmp_path):
    db_path = str(tmp_path / "manifest_authorization.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE managed_sites (
                id INTEGER PRIMARY KEY,
                web_id INTEGER NOT NULL,
                domain TEXT,
                lottery_type_id INTEGER,
                blueprint_name TEXT
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
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                title TEXT,
                UNIQUE(site_id, mechanism_key)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO managed_sites (id, web_id, domain, lottery_type_id, blueprint_name)
            VALUES (6, 6, 'www.twsaimahui.com', 3, 'twsaimahui')
            """
        )
        conn.execute(
            """
            INSERT INTO site_prediction_modules (id, site_id, mechanism_key, mode_id, status)
            VALUES
                (1, 6, 'title_470', 470, 1),
                (2, 6, 'legacy_475', 475, 1)
            """
        )

        reconcile_site_prediction_modules_to_blueprint(conn, site_ids=[6])
        rows = conn.execute(
            """
            SELECT mode_id, status
            FROM site_prediction_modules
            WHERE site_id = 6 AND mode_id IN (470, 475)
            ORDER BY mode_id
            """
        ).fetchall()

    assert [(int(row["mode_id"]), int(row["status"])) for row in rows] == [
        (470, 1),
        (475, 0),
    ]


def test_reconcile_uses_manifest_when_stored_profile_is_stale(tmp_path):
    db_path = str(tmp_path / "stale_profile_reconcile.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE managed_sites (
                id INTEGER PRIMARY KEY,
                web_id INTEGER NOT NULL,
                domain TEXT,
                lottery_type_id INTEGER,
                blueprint_name TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE site_blueprint_profiles (
                blueprint_name TEXT PRIMARY KEY,
                required_mode_ids_json TEXT NOT NULL,
                known_unavailable_mode_ids_json TEXT NOT NULL,
                blocked_items_json TEXT NOT NULL
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
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                title TEXT,
                UNIQUE(site_id, mechanism_key)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO managed_sites (id, web_id, domain, lottery_type_id, blueprint_name)
            VALUES (6, 6, 'www.twsaimahui.com', 3, 'twsaimahui')
            """
        )
        conn.execute(
            """
            INSERT INTO site_blueprint_profiles (
                blueprint_name, required_mode_ids_json,
                known_unavailable_mode_ids_json, blocked_items_json
            ) VALUES ('twsaimahui', '[470, 475]', '[]', '[]')
            """
        )
        conn.execute(
            """
            INSERT INTO site_prediction_modules (id, site_id, mechanism_key, mode_id, status)
            VALUES (1, 6, 'title_470', 470, 1), (2, 6, 'legacy_475', 475, 1)
            """
        )

        reconcile_site_prediction_modules_to_blueprint(conn, site_ids=[6])
        row = conn.execute(
            "SELECT status FROM site_prediction_modules WHERE site_id = 6 AND mode_id = 475"
        ).fetchone()

    assert int(row["status"]) == 0


def test_explicit_manifest_profile_sync_replaces_an_existing_stale_profile(tmp_path):
    """Existing PostgreSQL profile rows must change through a migration, not at runtime."""
    from database.versioned_migrations import _sync_site_blueprint_profiles_to_page_manifest
    from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key

    db_path = str(tmp_path / "manifest_profile_sync.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE site_blueprint_profiles (
                blueprint_name TEXT PRIMARY KEY,
                required_mode_ids_json TEXT NOT NULL,
                known_unavailable_mode_ids_json TEXT NOT NULL,
                blocked_items_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO site_blueprint_profiles (
                blueprint_name, required_mode_ids_json,
                known_unavailable_mode_ids_json, blocked_items_json,
                created_at, updated_at
            ) VALUES ('twsaimahui', '[475]', '[]', '[]', 'old', 'old')
            """
        )

        _sync_site_blueprint_profiles_to_page_manifest(conn)
        row = conn.execute(
            """
            SELECT required_mode_ids_json, updated_at
            FROM site_blueprint_profiles
            WHERE blueprint_name = 'twsaimahui'
            """
        ).fetchone()

    assert tuple(json.loads(str(row["required_mode_ids_json"]))) == required_mode_ids_for_site_key(
        "twsaimahui"
    )
    assert str(row["updated_at"]) != "old"


def test_twcf888_vendor_document_matches_the_live_blueprint():
    document_path = (
        Path(__file__).resolve().parents[4]
        / "frontend"
        / "public"
        / "vendor"
        / "twcf888.com"
        / "TWCF888_PREDICTION_MODULES.md"
    )

    assert parse_twcf888_document_mode_ids(document_path) == set(
        required_mode_ids_for_site_key("twcf888")
    )


def test_twsaimahui_vendor_document_matches_the_reachable_page_manifest():
    document_path = (
        Path(__file__).resolve().parents[4]
        / "frontend"
        / "public"
        / "vendor"
        / "twsaimahui"
        / "TWSAIMAHUI_PREDICTION_MODULES.md"
    )

    assert parse_twsaimahui_document_mode_ids(document_path) == set(
        required_mode_ids_for_site_key("twsaimahui")
    )


def test_shengshi8800_vendor_document_matches_the_reachable_page_manifest():
    document_path = (
        Path(__file__).resolve().parents[4]
        / "frontend"
        / "public"
        / "vendor"
        / "shengshi8800"
        / "SHENGSHI8800_PREDICTION_MODULES.md"
    )

    assert parse_shengshi8800_document_mode_ids(document_path) == set(
        required_mode_ids_for_site_key("shengshi8800")
    )


def test_reconciliation_script_validates_schema_without_importing_bootstrap_ddl():
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "reconcile_site_prediction_modules.py"
    script_text = script_path.read_text(encoding="utf-8")

    assert "ensure_admin_tables(args.db_path)" in script_text
    assert "_apply_legacy_schema_bootstrap" not in script_text


def test_reconciliation_script_audits_the_shengshi8800_document_and_all_managed_vendor_sites():
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "reconcile_site_prediction_modules.py"
    script_text = script_path.read_text(encoding="utf-8")

    assert "parse_shengshi8800_document_mode_ids" in script_text
    assert 'default="4,5,6,7,8,9,10"' in script_text
    assert 'or [4, 5, 6, 7, 8, 9, 10]' in script_text


def test_twcaibawang_vendor_composite_source_map_is_auditable():
    assert get_vendor_module_source_mode_ids() == {
        "wuxiao_wuma": (47, 69, 151),
        "public_yixiao_yima": (49, 44, 151),
        "shuangbo_12ma": (38,),
        "shujinguang": (44,),
        "daxiao_2tou": (57, 108),
        "tiandi_2xiao": (5, 251),
    }


def test_twjinniu_homepage_fixed_modes_are_declared_in_its_blueprint():
    source_path = (
        Path(__file__).resolve().parents[4]
        / "frontend"
        / "lib"
        / "twjinniu-homepage.ts"
    )

    assert parse_twjinniu_homepage_mode_ids(source_path) <= set(TWJINNIU_REQUIRED_MODE_IDS)


def test_frontend_dependency_audit_reports_composite_sources_separately():
    source_path = (
        Path(__file__).resolve().parents[4]
        / "frontend"
        / "lib"
        / "twjinniu-homepage.ts"
    )

    audit = audit_frontend_fixed_mode_dependencies(
        twjinniu_source_path=source_path,
        twcaibawang_source_mode_ids=get_vendor_module_source_mode_ids(),
    )

    assert audit["twjinniu"]["missing_from_blueprint"] == []
    assert audit["twcaibawang"]["composite_source_mode_ids"] == [
        5, 38, 44, 47, 49, 57, 69, 108, 151, 251,
    ]
    assert audit["twcaibawang"]["authorization"] == "runtime_site_prediction_modules"


def test_reconcile_disables_extra_rows_and_reenables_required_rows(tmp_path):
    db_path = str(tmp_path / "site_module_reconcile.sqlite3")
    _setup_audit_tables(db_path)

    with connect(db_path) as conn:
        result = reconcile_site_prediction_modules_to_blueprint(conn, site_ids=[8])
        rows = conn.execute(
            """
            SELECT mode_id, status
            FROM site_prediction_modules
            WHERE site_id = 8 AND mode_id IN (2, 44, 5)
            ORDER BY mode_id
            """
        ).fetchall()

    assert result[0]["site_id"] == 8
    assert result[0]["enabled"] == 1
    assert result[0]["disabled"] == 1
    assert result[0]["inserted"] >= 0
    assert [(int(row["mode_id"]), int(row["status"])) for row in rows] == [
        (2, 1),
        (5, 1),
        (44, 0),
    ]


def test_reconcile_keeps_twcaibawang_vendor_source_declared_by_the_manifest(tmp_path):
    db_path = str(tmp_path / "twcaibawang_vendor_source_reconcile.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE managed_sites (
                id INTEGER PRIMARY KEY,
                web_id INTEGER NOT NULL,
                domain TEXT,
                lottery_type_id INTEGER,
                blueprint_name TEXT
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
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                title TEXT,
                UNIQUE(site_id, mechanism_key)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO managed_sites (id, web_id, domain, lottery_type_id, blueprint_name)
            VALUES (5, 5, 'www.twcaibawang.com', 3, 'twcaibawang')
            """
        )
        conn.execute(
            """
            INSERT INTO site_prediction_modules (id, site_id, mechanism_key, mode_id, status)
            VALUES (1, 5, 'legacy_vendor_source', 44, 1)
            """
        )

        reconcile_site_prediction_modules_to_blueprint(conn, site_ids=[5])
        row = conn.execute(
            "SELECT status FROM site_prediction_modules WHERE id = 1"
        ).fetchone()

    assert int(row["status"]) == 1


def test_known_site_default_blueprint_is_migrated_to_its_dedicated_profile(tmp_path):
    db_path = str(tmp_path / "site_blueprint_profile_migration.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE managed_sites (
                id INTEGER PRIMARY KEY,
                web_id INTEGER NOT NULL,
                blueprint_name TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO managed_sites (id, web_id, blueprint_name) VALUES (7, 7, 'default')"
        )
        _backfill_site_blueprint_names(conn)
        row = conn.execute("SELECT blueprint_name FROM managed_sites WHERE id = 7").fetchone()

    assert row["blueprint_name"] == "twjinniu"
