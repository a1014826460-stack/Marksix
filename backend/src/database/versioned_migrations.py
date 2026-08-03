"""Explicit schema migrations for PostgreSQL production deployments.

The HTTP API and scheduler worker only validate the migration ledger.  Schema
DDL is performed by the explicit ``python -m database.versioned_migrations``
command while holding a transaction-scoped PostgreSQL advisory lock.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from database.connection import connect, detect_database_engine, utc_now


MIGRATION_TABLE = "schema_migrations"
CURRENT_SCHEMA_VERSION = 16
ADVISORY_LOCK_KEY = 734_605_197


class SchemaMigrationRequired(RuntimeError):
    """Raised when a production runtime sees an un-migrated database."""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    apply: Callable[[Any], None]


def _create_migration_ledger(conn: Any) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {MIGRATION_TABLE} (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


def _baseline_schema(conn: Any) -> None:
    """Apply the existing schema bootstrap once under the migration lock."""
    from database.bootstrap import _apply_legacy_schema_bootstrap

    _apply_legacy_schema_bootstrap(conn)


def _reconcile_created_prediction_tables(conn: Any) -> None:
    """Create or align every public payload mirror during explicit migrations."""
    from utils.created_prediction_store import ensure_created_prediction_table

    table_names = set(conn.list_tables("mode_payload_"))
    if conn.table_exists("mode_payload_tables"):
        rows = conn.execute("SELECT table_name FROM mode_payload_tables ORDER BY modes_id").fetchall()
        for row in rows:
            table_name = str(row["table_name"] or "")
            if table_name and conn.table_exists(table_name):
                table_names.add(table_name)

    for table_name in sorted(table_names):
        if table_name == "mode_payload_tables":
            continue
        ensure_created_prediction_table(conn, table_name, commit=False)


def _ensure_payload_source_table(
    conn: Any,
    *,
    modes_id: int,
    title: str,
) -> None:
    """Create a missing legacy public source table before importing its mirror."""
    table_exists = getattr(conn, "table_exists", None)
    if not callable(table_exists):
        return
    if table_exists(f"mode_payload_{int(modes_id)}"):
        return
    from database.connection import auto_increment_primary_key
    from database.schema.legacy import ensure_basic_prediction_payload_table

    ensure_basic_prediction_payload_table(
        conn,
        auto_increment_primary_key("id", conn.engine),
        modes_id=int(modes_id),
        title=title,
    )


def _sync_site_blueprint_profiles_to_page_manifest(conn: Any) -> None:
    """Apply reachable-page authorization sets through an explicit migration.

    This is deliberately migration-only: API and worker processes must never
    update site blueprint profiles as a side effect of ordinary startup.
    """
    if not conn.table_exists("site_blueprint_profiles"):
        return

    from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key

    for site_key in ("twcaibawang", "twsaimahui", "twjinniu", "twcf888"):
        conn.execute(
            """
            UPDATE site_blueprint_profiles
            SET required_mode_ids_json = ?, updated_at = ?
            WHERE blueprint_name = ?
            """,
            (
                json.dumps(
                    list(required_mode_ids_for_site_key(site_key)),
                    ensure_ascii=False,
                ),
                utc_now(),
                site_key,
            ),
        )


def _sync_shengshi8800_page_authorization(conn: Any) -> None:
    """Install the site-4 page profile and migrate only default assignments.

    Existing custom site-four profiles intentionally remain untouched. This
    migration changes authorization metadata only; it never modifies generated
    prediction rows or HTTP-facing payload data.
    """
    from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key

    if conn.table_exists("site_blueprint_profiles"):
        now = utc_now()
        conn.execute(
            """
            INSERT INTO site_blueprint_profiles (
                blueprint_name, required_mode_ids_json,
                known_unavailable_mode_ids_json, blocked_items_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (blueprint_name) DO UPDATE SET
                required_mode_ids_json = excluded.required_mode_ids_json,
                known_unavailable_mode_ids_json = excluded.known_unavailable_mode_ids_json,
                blocked_items_json = excluded.blocked_items_json,
                updated_at = excluded.updated_at
            """,
            (
                "shengshi8800",
                json.dumps(
                    list(required_mode_ids_for_site_key("shengshi8800")),
                    ensure_ascii=False,
                ),
                "[]",
                "[]",
                now,
                now,
            ),
        )

    if conn.table_exists("managed_sites"):
        conn.execute(
            """
            UPDATE managed_sites
            SET blueprint_name = ?
            WHERE web_id = 4
              AND (blueprint_name IS NULL OR blueprint_name = '' OR blueprint_name = 'default')
            """,
            ("shengshi8800",),
        )

def _install_twssz_site_profile(conn: Any) -> None:
    """Register the supplied twssz site and its reviewed replacement modes."""
    from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key

    now = utc_now()
    if conn.table_exists("site_blueprint_profiles"):
        conn.execute(
            """
            INSERT INTO site_blueprint_profiles (
                blueprint_name, required_mode_ids_json,
                known_unavailable_mode_ids_json, blocked_items_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (blueprint_name) DO UPDATE SET
                required_mode_ids_json = excluded.required_mode_ids_json,
                known_unavailable_mode_ids_json = excluded.known_unavailable_mode_ids_json,
                blocked_items_json = excluded.blocked_items_json,
                updated_at = excluded.updated_at
            """,
            (
                "twssz",
                json.dumps(list(required_mode_ids_for_site_key("twssz")), ensure_ascii=False),
                "[]",
                "[]",
                now,
                now,
            ),
        )

    if conn.table_exists("managed_sites"):
        conn.execute(
            """
            INSERT INTO managed_sites (
                id, web_id, name, domain, lottery_type_id, enabled,
                blueprint_name, announcement, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                web_id = excluded.web_id,
                name = excluded.name,
                domain = excluded.domain,
                lottery_type_id = excluded.lottery_type_id,
                enabled = excluded.enabled,
                blueprint_name = excluded.blueprint_name,
                notes = excluded.notes,
                updated_at = excluded.updated_at
            """,
            (
                9,
                9,
                "台湾神算子",
                "www.twssz.com",
                3,
                1,
                "twssz",
                "",
                "Seeded migration site for twssz vendor integration.",
                now,
                now,
            ),
        )

    # The managed-site record must exist before synchronizing its module rows.
    if conn.table_exists("site_prediction_modules"):
        from domains.prediction.generation_service import sync_site_prediction_modules

        sync_site_prediction_modules(conn, site_id=9)


# The supplied table contains only three-digit vendor terms.  They are imported
# with year 0 so they cannot be mistaken for verified calendar draw records.
_TWSSZ_STATIC_PREDICTION_HISTORY: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("204", ("兔,牛,猪,龙,蛇,羊,鼠", "兔,牛,猪,龙", "28,04,09,32,21,42,12,30,45,43", "兔,牛,猪", "28,04,09,32,21,42,12,30", "兔,牛", "28,04,09,32,21")),
    ("203", ("兔,蛇,狗,鸡,龙,猴,鼠", "兔,蛇,狗,鸡", "40,28,11,18,12,10,45,29,46,06", "兔,蛇,狗", "40,28,11,18,12,10,45,29", "兔,蛇", "40,28,11,18,12")),
    ("202", ("羊,鼠,狗,牛,鸡,猴,蛇", "羊,鼠,狗,牛", "12,36,28,18,23,22,45,38,02,11", "羊,鼠,狗", "12,36,28,18,23,22,45,38", "羊,鼠", "12,36,28,18,23")),
    ("201", ("鸡,兔,羊,马,猴,蛇,猪", "鸡,兔,羊,马", "34,46,36,14,31,30,11,13,02,38", "鸡,兔,羊", "34,46,36,14,31,30,11,13", "鸡,兔", "34,46,36,14,31")),
    ("200", ("鼠,蛇,虎,鸡,马,龙,狗", "鼠,蛇,虎,鸡", "19,31,28,18,23,05,49,39,37,34", "鼠,蛇,虎", "19,31,28,18,23,05,49,39", "鼠,蛇", "19,31,28,18,23")),
    ("199", ("虎,狗,鸡,龙,牛,猴,羊", "虎,狗,鸡,龙", "41,05,13,33,22,37,08,20,34,32", "虎,狗,鸡", "41,05,13,33,22,37,08,20", "虎,狗", "41,05,13,33,22")),
    ("198", ("虎,鼠,猴,龙,蛇,狗,羊", "虎,鼠,猴,龙", "17,05,01,30,07,33,28,13,36,03", "虎,鼠,猴", "17,05,01,30,07,33,28,13", "虎,鼠", "17,05,01,30,07")),
    ("197", ("猪,马,鸡,兔,狗,虎,猴", "猪,马,鸡,兔", "20,44,49,13,12,46,37,48,02,01", "猪,马,鸡", "20,44,49,13,12,46,37,48", "猪,马", "20,44,49,13,12")),
)

_TWSSZ_STATIC_HISTORY_MODULES: tuple[tuple[str, int], ...] = (
    ("mode_payload_44", 44),
    ("mode_payload_78", 78),
    ("mode_payload_481", 481),
    ("mode_payload_69", 69),
    ("mode_payload_51", 51),
    ("mode_payload_43", 43),
    ("mode_payload_66", 66),
)


def _import_twssz_static_prediction_history(conn: Any) -> None:
    """Make the vendor-supplied A级猛料 history available to the common API."""
    from utils.created_prediction_store import (
        ensure_created_prediction_table,
        upsert_created_prediction_row,
    )

    for value_index, (table_name, mode_id) in enumerate(_TWSSZ_STATIC_HISTORY_MODULES):
        _ensure_payload_source_table(conn, modes_id=mode_id, title=f"twssz imported mode {mode_id}")
        ensure_created_prediction_table(conn, table_name, commit=False)
        for term, values in _TWSSZ_STATIC_PREDICTION_HISTORY:
            upsert_created_prediction_row(
                conn,
                table_name,
                {
                    "type": "3",
                    "year": "0",
                    "term": term,
                    "web": "9",
                    "web_id": "9",
                    "modes_id": str(mode_id),
                    "content": values[value_index],
                },
                commit=False,
            )


def _sync_twssz_expanded_page_authorization(conn: Any) -> None:
    """Authorize the reviewed closest-mode mappings for every twssz data table."""
    _install_twssz_site_profile(conn)


def _sync_twssz_four_zodiac_module(conn: Any) -> None:
    """Install the 4-zodiac payload table and refresh Twssz authorization."""
    from database.connection import auto_increment_primary_key
    from database.schema.legacy import ensure_basic_prediction_payload_table

    ensure_basic_prediction_payload_table(
        conn,
        auto_increment_primary_key("id", conn.engine),
        modes_id=47,
        title="4肖中特",
    )
    _install_twssz_site_profile(conn)


def _install_twssz_five_no_hit_module(conn: Any) -> None:
    """Create the reviewed mode-485 payload table and refresh Twssz access."""
    from database.connection import auto_increment_primary_key
    from database.schema.legacy import ensure_basic_prediction_payload_table

    ensure_basic_prediction_payload_table(
        conn,
        auto_increment_primary_key("id", conn.engine),
        modes_id=485,
        title="内幕5不中",
    )
    _install_twssz_site_profile(conn)


def _relax_prediction_control_prefix_uniqueness(conn: Any) -> None:
    """Allow future generation when cross-site prefix diversity is exhausted."""
    if getattr(conn, "engine", "") != "postgres":
        return

    rows = conn.execute(
        """
        SELECT constraint_name, constraint_definition
        FROM (
            SELECT
                conname AS constraint_name,
                pg_get_constraintdef(oid) AS constraint_definition
            FROM pg_constraint
            WHERE conrelid = 'prediction_generation_controls'::regclass
              AND contype = 'u'
        ) AS unique_constraints
        """
    ).fetchall()
    for row in rows:
        constraint_name = str(row["constraint_name"] or "")
        constraint_definition = str(row["constraint_definition"] or "").lower()
        if not constraint_name or "prefix_hash" not in constraint_definition:
            continue
        escaped_name = constraint_name.replace('"', '""')
        conn.execute(
            f'ALTER TABLE prediction_generation_controls DROP CONSTRAINT IF EXISTS "{escaped_name}"'
        )


def _install_twbst528_site_profile(conn: Any) -> None:
    """Register the isolated Taiwan Baitong site and its homepage modules."""
    from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key

    now = utc_now()
    if conn.table_exists("site_blueprint_profiles"):
        conn.execute(
            """
            INSERT INTO site_blueprint_profiles (
                blueprint_name, required_mode_ids_json,
                known_unavailable_mode_ids_json, blocked_items_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (blueprint_name) DO UPDATE SET
                required_mode_ids_json = excluded.required_mode_ids_json,
                known_unavailable_mode_ids_json = excluded.known_unavailable_mode_ids_json,
                blocked_items_json = excluded.blocked_items_json,
                updated_at = excluded.updated_at
            """,
            (
                "twbst528",
                json.dumps(list(required_mode_ids_for_site_key("twbst528")), ensure_ascii=False),
                "[]",
                "[]",
                now,
                now,
            ),
        )

    if conn.table_exists("managed_sites"):
        conn.execute(
            """
            INSERT INTO managed_sites (
                id, web_id, name, domain, lottery_type_id, enabled,
                blueprint_name, announcement, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                web_id = excluded.web_id,
                name = excluded.name,
                domain = excluded.domain,
                lottery_type_id = excluded.lottery_type_id,
                enabled = excluded.enabled,
                blueprint_name = excluded.blueprint_name,
                notes = excluded.notes,
                updated_at = excluded.updated_at
            """,
            (
                10,
                10,
                "台湾百事通",
                "www.twbst528.com",
                3,
                1,
                "twbst528",
                "",
                "Seeded migration site for twbst528 vendor integration.",
                now,
                now,
            ),
        )

    # This creates only site-10 authorization rows. It never copies generated
    # history from any other web ID.
    if conn.table_exists("site_prediction_modules"):
        from domains.prediction.generation_service import sync_site_prediction_modules

        sync_site_prediction_modules(conn, site_id=10)


def _sync_twbst528_static_article_authorization(conn: Any) -> None:
    """Authorize the reviewed homepage-linked static article renderers."""
    _install_twbst528_site_profile(conn)


def _sync_twbst528_homepage_module_authorization(conn: Any) -> None:
    """Authorize the additional reviewed homepage renderers for site 10."""
    _install_twbst528_site_profile(conn)


def _install_twbst528_exact_prediction_modes(conn: Any) -> None:
    """Install exact vendor-mode tables before authorizing the expanded profile."""
    from database.connection import auto_increment_primary_key
    from database.schema.legacy import ensure_twbst528_prediction_tables

    ensure_twbst528_prediction_tables(conn, auto_increment_primary_key("id", conn.engine))
    _install_twbst528_site_profile(conn)


def _sync_twbst528_taiwan_pmt_image(conn: Any) -> None:
    """Authorize the site-10 image module added after the initial profile migration."""
    _install_twbst528_site_profile(conn)


def _sync_twbst528_exact_image_modules(conn: Any) -> None:
    """Refresh site 10 after adding its approved mode-474 and mode-476 images."""
    _install_twbst528_site_profile(conn)


def _install_twjsz666_site_profile(conn: Any) -> None:
    """Register Taiwan Golden Finger site 11 with reviewed shared modules."""
    from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key

    now = utc_now()
    if conn.table_exists("site_blueprint_profiles"):
        conn.execute(
            """
            INSERT INTO site_blueprint_profiles (
                blueprint_name, required_mode_ids_json,
                known_unavailable_mode_ids_json, blocked_items_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (blueprint_name) DO UPDATE SET
                required_mode_ids_json = excluded.required_mode_ids_json,
                known_unavailable_mode_ids_json = excluded.known_unavailable_mode_ids_json,
                blocked_items_json = excluded.blocked_items_json,
                updated_at = excluded.updated_at
            """,
            (
                "twjsz666",
                json.dumps(list(required_mode_ids_for_site_key("twjsz666")), ensure_ascii=False),
                "[]",
                "[]",
                now,
                now,
            ),
        )

    if conn.table_exists("managed_sites"):
        conn.execute(
            """
            INSERT INTO managed_sites (
                id, web_id, name, domain, lottery_type_id, enabled,
                blueprint_name, announcement, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                web_id = excluded.web_id,
                name = excluded.name,
                domain = excluded.domain,
                lottery_type_id = excluded.lottery_type_id,
                enabled = excluded.enabled,
                blueprint_name = excluded.blueprint_name,
                notes = excluded.notes,
                updated_at = excluded.updated_at
            """,
            (
                11,
                11,
                "台湾金手指",
                "www.twjsz666.com",
                3,
                1,
                "twjsz666",
                "",
                "Seeded migration site for twjsz666 vendor integration.",
                now,
                now,
            ),
        )

    if conn.table_exists("site_prediction_modules"):
        from domains.prediction.generation_service import sync_site_prediction_modules

        sync_site_prediction_modules(conn, site_id=11)


def _install_twjsz666_exact_prediction_modes(conn: Any) -> None:
    """Create and authorize the four exact mechanisms added for site 11."""
    from database.connection import auto_increment_primary_key
    from database.schema.legacy import ensure_twjsz666_prediction_tables

    ensure_twjsz666_prediction_tables(conn, auto_increment_primary_key("id", conn.engine))
    _install_twjsz666_site_profile(conn)


def _sync_twjsz666_composite_sources(conn: Any) -> None:
    """Authorize the composite sources used by the repaired homepage cards."""
    _install_twjsz666_site_profile(conn)


def _install_twwanli_site_profile(conn: Any) -> None:
    """Register Taiwan Wanli web 12 without copying another site's history."""
    from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key

    now = utc_now()
    if conn.table_exists("site_blueprint_profiles"):
        conn.execute(
            """
            INSERT INTO site_blueprint_profiles (
                blueprint_name, required_mode_ids_json,
                known_unavailable_mode_ids_json, blocked_items_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (blueprint_name) DO UPDATE SET
                required_mode_ids_json = excluded.required_mode_ids_json,
                known_unavailable_mode_ids_json = excluded.known_unavailable_mode_ids_json,
                blocked_items_json = excluded.blocked_items_json,
                updated_at = excluded.updated_at
            """,
            ("twwanli", json.dumps(list(required_mode_ids_for_site_key("twwanli")), ensure_ascii=False), "[]", "[]", now, now),
        )
    if conn.table_exists("managed_sites"):
        conn.execute(
            """
            INSERT INTO managed_sites (
                id, web_id, name, domain, lottery_type_id, enabled,
                blueprint_name, announcement, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                web_id = excluded.web_id, name = excluded.name, domain = excluded.domain,
                lottery_type_id = excluded.lottery_type_id, enabled = excluded.enabled,
                blueprint_name = excluded.blueprint_name, notes = excluded.notes, updated_at = excluded.updated_at
            """,
            (12, 12, "台湾万利网", "www.twwanli.com", 3, 1, "twwanli", "", "Seeded migration site for twwanli vendor integration.", now, now),
        )
    if conn.table_exists("site_prediction_modules"):
        from domains.prediction.generation_service import sync_site_prediction_modules
        sync_site_prediction_modules(conn, site_id=12)


def _install_twsyw_site_profile(conn: Any) -> None:
    """Register Taiwan Shenyu web 13 with its own authorized module profile."""
    from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key

    now = utc_now()
    if conn.table_exists("site_blueprint_profiles"):
        conn.execute(
            """
            INSERT INTO site_blueprint_profiles (
                blueprint_name, required_mode_ids_json,
                known_unavailable_mode_ids_json, blocked_items_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (blueprint_name) DO UPDATE SET
                required_mode_ids_json = excluded.required_mode_ids_json,
                known_unavailable_mode_ids_json = excluded.known_unavailable_mode_ids_json,
                blocked_items_json = excluded.blocked_items_json,
                updated_at = excluded.updated_at
            """,
            ("twsyw", json.dumps(list(required_mode_ids_for_site_key("twsyw")), ensure_ascii=False), "[]", "[]", now, now),
        )
    if conn.table_exists("managed_sites"):
        conn.execute(
            """
            INSERT INTO managed_sites (
                id, web_id, name, domain, lottery_type_id, enabled,
                blueprint_name, announcement, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                web_id = excluded.web_id, name = excluded.name, domain = excluded.domain,
                lottery_type_id = excluded.lottery_type_id, enabled = excluded.enabled,
                blueprint_name = excluded.blueprint_name, notes = excluded.notes, updated_at = excluded.updated_at
            """,
            (13, 13, "台湾神预网", "www.twsyw.com", 3, 1, "twsyw", "", "Seeded migration site for twsyw vendor integration.", now, now),
        )
    if conn.table_exists("site_prediction_modules"):
        from domains.prediction.generation_service import sync_site_prediction_modules
        sync_site_prediction_modules(conn, site_id=13)


def _sync_twssz_sxztu_image_authorization(conn: Any) -> None:
    """Refresh twssz after adding its exact mode-474 image module."""
    _install_twssz_site_profile(conn)


def _sync_twssz_title_five_authorization(conn: Any) -> None:
    """Authorize the existing twssz title_5 renderer on deployed site profiles."""
    _install_twssz_site_profile(conn)


MIGRATIONS: tuple[Migration, ...] = (
    Migration(1, "baseline_schema", _baseline_schema),
    Migration(2, "sync_site_prediction_page_authorization", _sync_site_blueprint_profiles_to_page_manifest),
    Migration(3, "sync_shengshi8800_page_authorization", _sync_shengshi8800_page_authorization),
    Migration(4, "install_twssz_vendor_site", _install_twssz_site_profile),
    Migration(5, "import_twssz_static_prediction_history", _import_twssz_static_prediction_history),
    Migration(6, "sync_twssz_expanded_page_authorization", _sync_twssz_expanded_page_authorization),
    Migration(7, "install_twssz_five_no_hit_module", _install_twssz_five_no_hit_module),
    Migration(8, "sync_twssz_four_zodiac_module", _sync_twssz_four_zodiac_module),
    Migration(9, "relax_prediction_control_prefix_uniqueness", _relax_prediction_control_prefix_uniqueness),
    Migration(10, "install_twbst528_vendor_site", _install_twbst528_site_profile),
    Migration(11, "sync_twbst528_static_article_authorization", _sync_twbst528_static_article_authorization),
    Migration(12, "sync_twbst528_homepage_module_authorization", _sync_twbst528_homepage_module_authorization),
    Migration(13, "install_twbst528_exact_prediction_modes", _install_twbst528_exact_prediction_modes),
    Migration(14, "sync_twbst528_taiwan_pmt_image", _sync_twbst528_taiwan_pmt_image),
    Migration(15, "install_twjsz666_vendor_site", _install_twjsz666_site_profile),
    Migration(16, "install_twjsz666_exact_prediction_modes", _install_twjsz666_exact_prediction_modes),
    Migration(17, "sync_twjsz666_composite_sources", _sync_twjsz666_composite_sources),
    Migration(18, "install_twwanli_vendor_site", _install_twwanli_site_profile),
    Migration(19, "install_twsyw_vendor_site", _install_twsyw_site_profile),
    Migration(20, "sync_twssz_sxztu_image_authorization", _sync_twssz_sxztu_image_authorization),
    Migration(21, "sync_twbst528_exact_image_modules", _sync_twbst528_exact_image_modules),
    Migration(22, "sync_twwanli_five_element_authorization", _install_twwanli_site_profile),
    Migration(23, "sync_twwanli_six_xiao_authorization", _install_twwanli_site_profile),
    Migration(24, "sync_twssz_title_five_authorization", _sync_twssz_title_five_authorization),
)


def _applied_versions(conn: Any) -> set[int]:
    rows = conn.execute(f"SELECT version FROM {MIGRATION_TABLE}").fetchall()
    return {int(row["version"]) for row in rows}


def run_migrations(db_path: str | Path) -> list[int]:
    """Apply pending PostgreSQL schema migrations under an advisory lock."""
    if detect_database_engine(db_path) != "postgres":
        raise RuntimeError("版本化迁移命令仅支持 PostgreSQL。SQLite 仅用于显式测试/bootstrap。")

    with connect(db_path) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(?)", (ADVISORY_LOCK_KEY,))
        _create_migration_ledger(conn)
        applied = _applied_versions(conn)
        newly_applied: list[int] = []
        for migration in MIGRATIONS:
            if migration.version in applied:
                continue
            migration.apply(conn)
            conn.execute(
                f"INSERT INTO {MIGRATION_TABLE} (version, name, applied_at) VALUES (?, ?, ?)",
                (migration.version, migration.name, utc_now()),
            )
            newly_applied.append(migration.version)
        _reconcile_created_prediction_tables(conn)
        return newly_applied


def validate_runtime_schema(db_path: str | Path) -> None:
    """Verify that an API/worker PostgreSQL target has all migrations applied."""
    if detect_database_engine(db_path) != "postgres":
        return

    expected = {migration.version for migration in MIGRATIONS}
    with connect(db_path) as conn:
        if not conn.table_exists(MIGRATION_TABLE):
            raise SchemaMigrationRequired(
                "数据库尚未执行版本化迁移；请先运行 python -m database.versioned_migrations。"
            )
        missing = expected - _applied_versions(conn)
    if missing:
        missing_text = ", ".join(str(version) for version in sorted(missing))
        raise SchemaMigrationRequired(
            f"数据库缺少 schema migration 版本 {missing_text}；"
            "请先运行 python -m database.versioned_migrations。"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply Liuhecai PostgreSQL schema migrations.")
    parser.add_argument("--db-path", "--db_path", dest="db_path", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    applied = run_migrations(args.db_path)
    if applied:
        print(f"Applied schema migrations: {', '.join(str(version) for version in applied)}")
    else:
        print("Schema migrations are already current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
