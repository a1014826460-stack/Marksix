from __future__ import annotations

from pathlib import Path

from db import connect
from database.schema.prediction import _backfill_site_blueprint_names
from domains.prediction.site_module_audit import (
    audit_runtime_module_sets,
    audit_frontend_fixed_mode_dependencies,
    parse_twcf888_document_mode_ids,
    parse_twjinniu_homepage_mode_ids,
    reconcile_site_prediction_modules_to_blueprint,
)
from domains.prediction.site_module_blueprints import (
    TWCF888_REQUIRED_MODE_IDS,
    TWJINNIU_REQUIRED_MODE_IDS,
)
from vendor.homepage_modules import get_vendor_module_source_mode_ids


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
                (3, 8, 'disabled-required', 51, 0)
            """
        )


def test_runtime_audit_reports_missing_disabled_and_extra_mode_ids(tmp_path):
    db_path = str(tmp_path / "site_module_audit.sqlite3")
    _setup_audit_tables(db_path)

    with connect(db_path) as conn:
        audit = audit_runtime_module_sets(conn, site_ids=[8])

    assert audit == [
        {
            "site_id": 8,
            "web_id": 8,
            "blueprint_name": "twcf888",
            "blueprint_mode_ids": list(TWCF888_REQUIRED_MODE_IDS),
            "enabled_mode_ids": [2, 44],
            "missing_from_runtime": [
                mode_id for mode_id in TWCF888_REQUIRED_MODE_IDS if mode_id != 2
            ],
            "enabled_outside_blueprint": [44],
            "vendor_dependency_mode_ids": [],
            "enabled_outside_authorized_sources": [44],
        }
    ]


def test_twcf888_vendor_document_matches_the_live_blueprint():
    document_path = (
        Path(__file__).resolve().parents[4]
        / "frontend"
        / "public"
        / "vendor"
        / "twcf888.com"
        / "TWCF888_PREDICTION_MODULES.md"
    )

    assert parse_twcf888_document_mode_ids(document_path) == set(TWCF888_REQUIRED_MODE_IDS)


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
            WHERE site_id = 8 AND mode_id IN (2, 44, 51)
            ORDER BY mode_id
            """
        ).fetchall()

    assert result[0]["site_id"] == 8
    assert result[0]["enabled"] == 1
    assert result[0]["disabled"] == 1
    assert result[0]["inserted"] >= 0
    assert [(int(row["mode_id"]), int(row["status"])) for row in rows] == [
        (2, 1),
        (44, 0),
        (51, 1),
    ]


def test_reconcile_does_not_keep_twcaibawang_vendor_sources_outside_blueprint(tmp_path):
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

    assert int(row["status"]) == 0


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
