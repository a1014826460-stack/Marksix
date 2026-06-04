"""Default bootstrap seed data."""

from __future__ import annotations

from typing import Any

from runtime_config import get_bootstrap_config_value

HK_NAMES = ("香港彩", "六肖彩")
MACAU_NAME = "澳门彩"
TAIWAN_NAME = "台湾彩"


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
                "www.twjinniu.com",
                taiwan_lottery_id,
                "twjinniu",
                "",
                "Seeded bootstrap site for twjinniu vendor integration.",
                now,
                now,
            ),
        )

    _sync_modules(conn)
