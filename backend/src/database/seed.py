"""Default bootstrap seed data."""

from __future__ import annotations

from typing import Any

from db import auto_increment_primary_key
from runtime_config import get_bootstrap_config_value

from database.yijuzhenyan_seed_rows import YIJUZHENYAN_TEXT_POOL_ROWS

HK_NAMES = ("香港彩", "六肖彩")
MACAU_NAME = "澳门彩"
TAIWAN_NAME = "台湾彩"


YIJUZHENYAN_TABLE = "mode_payload_50"
YIJUZHENYAN_MAPPING_TABLE = "text_history_mappings"
YIJUZHENYAN_METADATA_TABLE = "mode_payload_tables"
YIJUZHENYAN_SEED_WEB = "seed_pool"
YIJUZHENYAN_SEED_TYPE = "yijuzhenyan"
YIJUZHENYAN_SEED_YEAR = "0"
YIJUZHENYAN_MODE_ID = 50


def _merge_lottery_type_alias(conn: Any, canonical_name: str, *aliases: str) -> None:
    canonical = conn.execute(
        "SELECT id FROM lottery_types WHERE name = ? ORDER BY id LIMIT 1",
        (canonical_name,),
    ).fetchone()

    for alias in aliases:
        alias_rows = conn.execute(
            "SELECT id FROM lottery_types WHERE name = ? ORDER BY id",
            (alias,),
        ).fetchall()
        if not alias_rows:
            continue

        if canonical:
            canonical_id = int(canonical["id"])
            for row in alias_rows:
                alias_id = int(row["id"])
                if alias_id == canonical_id:
                    continue
                if conn.table_exists("lottery_draws"):
                    conn.execute(
                        """
                        DELETE FROM lottery_draws
                        WHERE lottery_type_id = ?
                          AND EXISTS (
                              SELECT 1
                              FROM lottery_draws canonical_draws
                              WHERE canonical_draws.lottery_type_id = ?
                                AND canonical_draws.year = lottery_draws.year
                                AND canonical_draws.term = lottery_draws.term
                          )
                        """,
                        (alias_id, canonical_id),
                    )
                    conn.execute(
                        "UPDATE lottery_draws SET lottery_type_id = ? WHERE lottery_type_id = ?",
                        (canonical_id, alias_id),
                    )
                for table_name in ("managed_sites", "scheduler_tasks", "error_logs"):
                    if not conn.table_exists(table_name):
                        continue
                    if "lottery_type_id" not in set(conn.table_columns(table_name)):
                        continue
                    conn.execute(
                        f"UPDATE {table_name} SET lottery_type_id = ? WHERE lottery_type_id = ?",
                        (canonical_id, alias_id),
                    )
                conn.execute("DELETE FROM lottery_types WHERE id = ?", (alias_id,))
            continue

        first_alias = alias_rows[0]
        conn.execute(
            "UPDATE lottery_types SET name = ? WHERE id = ?",
            (canonical_name, int(first_alias["id"])),
        )
        canonical = {"id": int(first_alias["id"])}


def _ensure_yijuzhenyan_source_table(conn: Any) -> None:
    if conn.table_exists(YIJUZHENYAN_TABLE):
        return

    pk_sql = auto_increment_primary_key("id", conn.engine)
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {YIJUZHENYAN_TABLE} (
            {pk_sql},
            web TEXT,
            type TEXT,
            year TEXT,
            term TEXT,
            res_code TEXT,
            res_sx TEXT,
            res_color TEXT,
            status INTEGER,
            title TEXT,
            content TEXT,
            jiexi TEXT
        )
        """
    )


def _ensure_mode_payload_metadata_table(conn: Any) -> None:
    if conn.table_exists(YIJUZHENYAN_METADATA_TABLE):
        return

    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {YIJUZHENYAN_METADATA_TABLE} (
            modes_id INTEGER,
            title TEXT,
            filename TEXT,
            table_name TEXT,
            record_count INTEGER,
            created_at TEXT,
            is_image INTEGER,
            is_text INTEGER
        )
        """
    )


def _sync_yijuzhenyan_metadata(conn: Any, *, now: str) -> bool:
    _ensure_mode_payload_metadata_table(conn)
    total_rows = int(
        conn.execute(f"SELECT COUNT(*) AS total FROM {YIJUZHENYAN_TABLE}").fetchone()["total"] or 0
    )
    existing = conn.execute(
        f"""
        SELECT modes_id, title, table_name, record_count, is_text, is_image
        FROM {YIJUZHENYAN_METADATA_TABLE}
        WHERE modes_id = ?
        LIMIT 1
        """,
        (YIJUZHENYAN_MODE_ID,),
    ).fetchone()

    desired = {
        "title": "一句真言",
        "table_name": YIJUZHENYAN_TABLE,
        "record_count": total_rows,
        "is_text": 1,
        "is_image": 0,
    }
    if existing:
        current = {
            "title": str(existing["title"] or ""),
            "table_name": str(existing["table_name"] or ""),
            "record_count": int(existing["record_count"] or 0),
            "is_text": int(existing["is_text"] or 0),
            "is_image": int(existing["is_image"] or 0),
        }
        if current == desired:
            return False
        conn.execute(
            f"""
            UPDATE {YIJUZHENYAN_METADATA_TABLE}
            SET title = ?, table_name = ?, record_count = ?, is_text = ?, is_image = ?
            WHERE modes_id = ?
            """,
            (
                desired["title"],
                desired["table_name"],
                desired["record_count"],
                desired["is_text"],
                desired["is_image"],
                YIJUZHENYAN_MODE_ID,
            ),
        )
        return True

    columns = set(conn.table_columns(YIJUZHENYAN_METADATA_TABLE))
    insert_columns = ["modes_id", "title", "table_name", "record_count", "is_text", "is_image"]
    values: list[Any] = [
        YIJUZHENYAN_MODE_ID,
        desired["title"],
        desired["table_name"],
        desired["record_count"],
        desired["is_text"],
        desired["is_image"],
    ]
    if "filename" in columns:
        insert_columns.append("filename")
        values.append("")
    if "created_at" in columns:
        insert_columns.append("created_at")
        values.append(now)

    placeholders = ", ".join("?" for _ in insert_columns)
    conn.execute(
        f"""
        INSERT INTO {YIJUZHENYAN_METADATA_TABLE} ({", ".join(insert_columns)})
        VALUES ({placeholders})
        """,
        values,
    )
    return True


def _rebuild_text_history_mappings(conn: Any) -> None:
    from utils.rebuild_text_mappings import (
        get_text_mode_tables,
        insert_from_mode_table,
        rebuild_mapping_table,
    )

    target_modes = get_text_mode_tables(conn)
    rebuild_mapping_table(conn)
    for mode in target_modes:
        table_name = str(mode["table_name"] or "")
        modes_id = int(mode["modes_id"] or 0)
        if not table_name or modes_id <= 0 or not conn.table_exists(table_name):
            continue
        insert_from_mode_table(conn, modes_id, table_name)


def seed_yijuzhenyan_text_pool(conn: Any, *, now: str) -> dict[str, Any]:
    _ensure_yijuzhenyan_source_table(conn)

    inserted = 0
    updated = 0
    columns = set(conn.table_columns(YIJUZHENYAN_TABLE))
    next_id = 0
    if "id" in columns:
        max_row = conn.execute(
            f"SELECT MAX(CAST(id AS INTEGER)) AS max_id FROM {YIJUZHENYAN_TABLE}"
        ).fetchone()
        next_id = int(max_row["max_id"] or 0) + 1

    for index, row in enumerate(YIJUZHENYAN_TEXT_POOL_ROWS, start=1):
        term = str(9000 + index)
        existing = conn.execute(
            f"""
            SELECT id, title, content, jiexi, status
            FROM {YIJUZHENYAN_TABLE}
            WHERE web = ? AND type = ? AND year = ? AND term = ?
            LIMIT 1
            """,
            (
                YIJUZHENYAN_SEED_WEB,
                YIJUZHENYAN_SEED_TYPE,
                YIJUZHENYAN_SEED_YEAR,
                term,
            ),
        ).fetchone()
        if existing:
            current = (
                str(existing["title"] or ""),
                str(existing["content"] or ""),
                str(existing["jiexi"] or ""),
                int(existing["status"] or 0),
            )
            desired = (
                str(row["title"] or ""),
                str(row["content"] or ""),
                str(row["jiexi"] or ""),
                1,
            )
            if current != desired:
                conn.execute(
                    f"""
                    UPDATE {YIJUZHENYAN_TABLE}
                    SET status = 1, title = ?, content = ?, jiexi = ?
                    WHERE id = ?
                    """,
                    (
                        desired[0],
                        desired[1],
                        desired[2],
                        existing["id"],
                    ),
                )
                updated += 1
            continue

        if "id" in columns:
            conn.execute(
                f"""
                INSERT INTO {YIJUZHENYAN_TABLE} (
                    id, web, type, year, term,
                    res_code, res_sx, res_color, status,
                    title, content, jiexi
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    next_id,
                    YIJUZHENYAN_SEED_WEB,
                    YIJUZHENYAN_SEED_TYPE,
                    YIJUZHENYAN_SEED_YEAR,
                    term,
                    "",
                    "",
                    "",
                    1,
                    str(row["title"] or ""),
                    str(row["content"] or ""),
                    str(row["jiexi"] or ""),
                ),
            )
            next_id += 1
        else:
            conn.execute(
                f"""
                INSERT INTO {YIJUZHENYAN_TABLE} (
                    web, type, year, term,
                    res_code, res_sx, res_color, status,
                    title, content, jiexi
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    YIJUZHENYAN_SEED_WEB,
                    YIJUZHENYAN_SEED_TYPE,
                    YIJUZHENYAN_SEED_YEAR,
                    term,
                    "",
                    "",
                    "",
                    1,
                    str(row["title"] or ""),
                    str(row["content"] or ""),
                    str(row["jiexi"] or ""),
                ),
            )
        inserted += 1

    metadata_changed = _sync_yijuzhenyan_metadata(conn, now=now)
    needs_rebuild = (
        inserted > 0
        or updated > 0
        or metadata_changed
        or not conn.table_exists(YIJUZHENYAN_MAPPING_TABLE)
    )
    if needs_rebuild:
        _rebuild_text_history_mappings(conn)

    return {
        "inserted": inserted,
        "updated": updated,
        "metadata_changed": metadata_changed,
        "rebuilt_mappings": needs_rebuild,
    }


def seed_default_lottery_types(conn: Any, *, now: str) -> None:
    """Seed the built-in lottery types and normalize legacy English names."""
    _merge_lottery_type_alias(conn, HK_NAMES[0], HK_NAMES[1], "Hong Kong", "Liuhecai")
    _merge_lottery_type_alias(conn, MACAU_NAME, "Macau")
    _merge_lottery_type_alias(conn, TAIWAN_NAME, "Taiwan")
    defaults = [
        (
            HK_NAMES[0],
            str(get_bootstrap_config_value("draw.hk_default_draw_time", "21:30")),
            str(get_bootstrap_config_value("draw.hk_default_collect_url", "https://www.lnlllt.com/api.php")),
        ),
        (
            MACAU_NAME,
            str(get_bootstrap_config_value("draw.macau_default_draw_time", "21:30")),
            str(get_bootstrap_config_value("draw.macau_default_collect_url", "https://www.lnlllt.com/api.php")),
        ),
        (
            TAIWAN_NAME,
            str(get_bootstrap_config_value("draw.taiwan_default_draw_time", "22:30")),
            "",
        ),
    ]
    for lottery_name, draw_time, collect_url in defaults:
        exists = conn.execute(
            "SELECT COUNT(*) AS total FROM lottery_types WHERE name = ?",
            (lottery_name,),
        ).fetchone()["total"]
        if exists:
            continue
        conn.execute(
            """
            INSERT INTO lottery_types
                (name, draw_time, collect_url, status, created_at, updated_at)
            VALUES (?, ?, ?, 1, ?, ?)
            """,
            (lottery_name, draw_time, collect_url, now, now),
        )


def seed_bootstrap_data(conn: Any, now: str) -> None:
    """Seed the default admin, lottery types, site, and prediction modules."""
    from auth import hash_password as _hash_password
    from admin.prediction import sync_site_prediction_modules as _sync_modules

    admin_count = int(
        conn.execute("SELECT COUNT(*) AS total FROM admin_users").fetchone()["total"]
        or 0
    )
    if admin_count == 0:
        admin_user = str(get_bootstrap_config_value("admin.username", "admin"))
        admin_display = str(get_bootstrap_config_value("admin.display_name", "系统管理员"))
        admin_pass = str(get_bootstrap_config_value("admin.password", "admin123"))
        admin_role = str(get_bootstrap_config_value("admin.role", "super_admin"))
        conn.execute(
            """
            INSERT INTO admin_users (
                username, display_name, password_hash, role, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 1, ?, ?)
            """,
            (
                admin_user,
                admin_display,
                _hash_password(admin_pass),
                admin_role,
                now,
                now,
            ),
        )

    seed_default_lottery_types(conn, now=now)

    default_lottery_id = conn.execute(
        "SELECT id FROM lottery_types ORDER BY id LIMIT 1"
    ).fetchone()["id"]
    taiwan_lottery_row = conn.execute(
        "SELECT id FROM lottery_types WHERE name = ? ORDER BY id LIMIT 1",
        (TAIWAN_NAME,),
    ).fetchone()
    taiwan_lottery_id = int(taiwan_lottery_row["id"]) if taiwan_lottery_row else int(default_lottery_id)

    site_count = int(
        conn.execute("SELECT COUNT(*) AS total FROM managed_sites").fetchone()["total"]
        or 0
    )
    if site_count == 0:
        site_name = str(get_bootstrap_config_value("site.default_site_name", "默认站点"))
        site_domain = str(get_bootstrap_config_value("site.default_domain", "admin.shengshi8800.com"))
        site_announcement = str(get_bootstrap_config_value("site.default_announcement", ""))
        site_notes = str(get_bootstrap_config_value("site.default_notes", ""))
        site_web_id = int(
            get_bootstrap_config_value(
                "site.default_web_id",
                get_bootstrap_config_value("site.start_web_id", 1),
            )
        )
        conn.execute(
            """
            INSERT INTO managed_sites (
                web_id, name, domain, lottery_type_id, enabled,
                blueprint_name, announcement, notes,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
            """,
            (
                site_web_id,
                site_name,
                site_domain,
                default_lottery_id,
                "default",
                site_announcement,
                site_notes,
                now,
                now,
            ),
        )
    else:
        conn.execute(
            "UPDATE managed_sites SET lottery_type_id = COALESCE(lottery_type_id, ?)",
            (default_lottery_id,),
        )
        conn.execute(
            "UPDATE managed_sites SET web_id = COALESCE(web_id, id) WHERE web_id IS NULL"
        )

    twjinniu_exists = conn.execute(
        "SELECT id FROM managed_sites WHERE web_id = ? LIMIT 1",
        (7,),
    ).fetchone()
    if not twjinniu_exists:
        conn.execute(
            """
            INSERT INTO managed_sites (
                id, web_id, name, domain, lottery_type_id, enabled,
                blueprint_name, announcement, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
            """,
            (
                7,
                7,
                "台湾金牛论坛",
                "www.twtongtian.com",
                taiwan_lottery_id,
                "twjinniu",
                "",
                "Seeded bootstrap site for twjinniu vendor integration.",
                now,
                now,
            ),
        )

    twcf888_exists = conn.execute(
        "SELECT id FROM managed_sites WHERE web_id = ? LIMIT 1",
        (8,),
    ).fetchone()
    if not twcf888_exists:
        conn.execute(
            """
            INSERT INTO managed_sites (
                id, web_id, name, domain, lottery_type_id, enabled,
                blueprint_name, announcement, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
            """,
            (
                8,
                8,
                "?????",
                "www.twcf888.com",
                taiwan_lottery_id,
                "twcf888",
                "",
                "Seeded bootstrap site for twcf888 vendor integration.",
                now,
                now,
            ),
        )

    twssz_exists = conn.execute(
        "SELECT id FROM managed_sites WHERE web_id = ? LIMIT 1",
        (9,),
    ).fetchone()
    if not twssz_exists:
        conn.execute(
            """
            INSERT INTO managed_sites (
                id, web_id, name, domain, lottery_type_id, enabled,
                blueprint_name, announcement, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
            """,
            (
                9,
                9,
                "台湾神算子",
                "www.twssz.com",
                taiwan_lottery_id,
                "twssz",
                "",
                "Seeded bootstrap site for twssz vendor integration.",
                now,
                now,
            ),
        )

    _sync_modules(conn)
    seed_yijuzhenyan_text_pool(conn, now=now)
