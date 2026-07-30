"""site_prediction_modules / mechanism_status 表 —— 预测模块与机制状态。"""

from __future__ import annotations

import json
from typing import Any

from database.migrations import add_column_if_missing
from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key


DEFAULT_SITE_BLUEPRINT_NAME = "default"
SHENGSHI8800_BLUEPRINT_NAME = "shengshi8800"
TWCAIBAWANG_BLUEPRINT_NAME = "twcaibawang"
TWSAIMAHUI_BLUEPRINT_NAME = "twsaimahui"
TWJINNIU_BLUEPRINT_NAME = "twjinniu"
TWCF888_BLUEPRINT_NAME = "twcf888"
TWSSZ_BLUEPRINT_NAME = "twssz"
TWBST528_BLUEPRINT_NAME = "twbst528"
TWJSZ666_BLUEPRINT_NAME = "twjsz666"

DEFAULT_REQUIRED_MODE_IDS = (
    2, 3, 5, 8, 9, 10, 12, 15, 20, 22, 24, 26, 27, 28, 30, 31, 34, 38, 39,
    41, 42, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 56, 57, 58, 60, 61, 62,
    63, 69, 88, 108, 116, 123, 132, 141, 143, 144, 145, 147, 149, 151, 152,
    155, 157, 158, 159, 197, 244, 246, 251, 295, 333, 336, 470, 471, 472,
    473, 474, 475, 476, 478,
)
DEFAULT_KNOWN_UNAVAILABLE_MODE_IDS = (63, 64, 65, 66, 67, 68, 151)
TWCAIBAWANG_REQUIRED_MODE_IDS = (
    12, 26, 34, 38, 49, 50, 52, 54, 56, 57, 58, 60, 197, 472, 479, 480, 481,
    482, 483, 484,
)
TWJINNIU_REQUIRED_MODE_IDS = (
    5, 12, 14, 20, 15, 26, 31, 38, 43, 47, 48, 49, 50, 51, 53, 56, 66, 72, 74,
    77, 78, 79, 81, 83, 103, 108, 110, 117, 123, 132, 142, 143, 144, 151,
    173, 180, 198, 219, 279, 472, 474, 476, 479, 480, 481, 482, 483, 484,
)
TWSAIMAHUI_REQUIRED_MODE_IDS = (
    3, 5, 8, 9, 10, 12, 15, 20, 22, 24, 26, 27, 28, 30, 31, 39, 41, 42, 45,
    46, 47, 48, 49, 50, 51, 54, 56, 57, 58, 61, 62, 63, 69, 88, 108, 116, 123,
    132, 141, 143, 144, 145, 147, 149, 151, 152, 155, 157, 158, 159, 197, 244,
    246, 251, 295, 336, 470, 471, 472, 473, 475, 476, 478,
)
TWJINNIU_BLOCKED_ITEMS = ()
# twcf888 v1 is intentionally conservative: only confirmed live mappings are
# required. Everything else stays blocked or snapshot-only.
TWCF888_REQUIRED_MODE_IDS = (
    2, 5, 12, 14, 15, 20, 26, 27, 28, 38, 41, 42, 43, 45, 47, 49, 50, 51,
    53, 54, 57, 66, 69, 74, 88, 95, 98, 100, 103, 122, 132, 143, 180, 197,
    198, 224, 226, 279, 470, 472, 473, 482, 483,
)

TWCF888_BLOCKED_ITEMS = ()

# Override the initial conservative v1 set with the currently confirmed live
# mappings. Keeping the redefinition here avoids touching older mojibake rows
# one-by-one while still making the runtime/profile data deterministic.
TWCF888_REQUIRED_MODE_IDS = (
    2, 5, 12, 14, 15, 20, 26, 27, 28, 38, 41, 42, 43, 45, 47, 49, 50, 51,
    53, 54, 57, 66, 69, 74, 88, 95, 98, 100, 103, 122, 132, 143, 180, 197,
    198, 224, 226, 279, 470, 472, 473, 482, 483,
)

TWCF888_BLOCKED_ITEMS = ()
TWSAIMAHUI_KNOWN_UNAVAILABLE_MODE_IDS = (
    5, 9, 10, 15, 22, 24, 27, 30, 39, 41, 47, 48, 63, 88, 116, 123, 132, 141,
    143, 144, 145, 147, 149, 151, 152, 155, 157, 158, 159, 244, 246, 251, 295,
    336,
)
TWCAIBAWANG_BLOCKED_ITEMS = (
    {
        "frontend_module": "五肖五码",
        "page_title": "五肖五码",
        "reason": "Homepage block combines 五肖/四肖/三肖/二肖 and 五码/四码/三码/二码 in one custom static layout. No single existing mechanism matches its exact payload shape yet.",
        "expected_fields": ("issue", "xiao_5", "xiao_4", "xiao_3", "xiao_2", "code_5", "code_4", "code_3", "code_2"),
        "status": "blocked_exact_payload_mapping",
    },
    {
        "frontend_module": "公开一肖一码",
        "page_title": "一肖一码",
        "reason": "Homepage block contains 九肖/七肖/五肖/三肖 plus 14码/8码/5码 and a final 一肖一码 summary. Existing mechanisms cover parts of it, but not this exact combined payload shape.",
        "expected_fields": ("issue", "xiao_9", "xiao_7", "xiao_5", "xiao_3", "code_14", "code_8", "code_5", "best_xiao", "best_code"),
        "status": "blocked_exact_payload_mapping",
    },
    {
        "frontend_module": "高手榜单",
        "page_title": "高手榜单",
        "reason": "This section links to standalone detail pages like 11169.html and needs article/detail content APIs rather than prediction-module history rows.",
        "expected_fields": ("id", "slug", "title", "term", "html"),
        "status": "blocked_requires_article_api",
    },
    {
        "frontend_module": "输尽六",
        "page_title": "输尽六",
        "reason": "The homepage section name is clear, but its exact backend payload contract and matching mechanism are not yet confirmed from existing tables.",
        "expected_fields": ("issue", "content", "result_text"),
        "status": "blocked_unconfirmed_mechanism_mapping",
    },
    {
        "frontend_module": "六肖中特",
        "page_title": "六肖中特网",
        "reason": "The current backend has generic tail-based mechanisms, but this homepage module's exact six-tail layout and source mode_id are not confirmed yet.",
        "expected_fields": ("issue", "tail_values", "result_text"),
        "status": "blocked_unconfirmed_mode_id",
    },
    {
        "frontend_module": "四行中特",
        "page_title": "四行中特",
        "reason": "Current backend ships a stable 3行 mechanism (mode 53), but the homepage requests four-line semantics. This needs either a confirmed existing mode_id or a new mechanism.",
        "expected_fields": ("issue", "element_values", "result_text"),
        "status": "blocked_missing_matching_mechanism",
    },
    {
        "frontend_module": "绝杀10码",
        "page_title": "绝杀10码",
        "reason": "The site layout is known, but the exact source mode_id and stored payload columns still need confirmation from PostgreSQL history tables.",
        "expected_fields": ("issue", "codes", "result_text"),
        "status": "blocked_unconfirmed_mode_id",
    },
)
TWSAIMAHUI_BLOCKED_ITEMS = (
    {
        "frontend_module": "019liubuzhong.js",
        "endpoint": "/api/kaijiang/rd70i73lziizczak/0gmqnw/1",
        "page_title": "六肖不中",
        "reason": "Current local data source does not match 六不中 payload semantics. mode_payload_333 is 天地4肖 not u6_code data.",
        "expected_fields": ("term", "u6_code", "res_code", "res_sx"),
        "status": "blocked_data_source",
    },
)

# Backward-compatible constant exports must mirror the same page inventory
# used by runtime profiles and explicit authorization migrations.
TWCAIBAWANG_REQUIRED_MODE_IDS = required_mode_ids_for_site_key("twcaibawang")
TWSAIMAHUI_REQUIRED_MODE_IDS = required_mode_ids_for_site_key("twsaimahui")
TWJINNIU_REQUIRED_MODE_IDS = required_mode_ids_for_site_key("twjinniu")
TWCF888_REQUIRED_MODE_IDS = required_mode_ids_for_site_key("twcf888")
TWSSZ_REQUIRED_MODE_IDS = required_mode_ids_for_site_key("twssz")
TWBST528_REQUIRED_MODE_IDS = required_mode_ids_for_site_key("twbst528")
TWJSZ666_REQUIRED_MODE_IDS = required_mode_ids_for_site_key("twjsz666")


def _seed_site_blueprint_profiles(conn: Any) -> None:
    # Bootstrap profiles use the same reachable-page inventory as the explicit
    # authorization migration. Runtime never mutates these rows.
    now_row = conn.execute("SELECT CURRENT_TIMESTAMP AS current_ts").fetchone()
    now = str(now_row["current_ts"] or "")
    profiles = (
        {
            "name": DEFAULT_SITE_BLUEPRINT_NAME,
            "required_mode_ids": DEFAULT_REQUIRED_MODE_IDS,
            "known_unavailable_mode_ids": DEFAULT_KNOWN_UNAVAILABLE_MODE_IDS,
            "blocked_items": (),
        },
        {
            "name": SHENGSHI8800_BLUEPRINT_NAME,
            "required_mode_ids": required_mode_ids_for_site_key("shengshi8800"),
            "known_unavailable_mode_ids": (),
            "blocked_items": (),
        },
        {
            "name": TWCAIBAWANG_BLUEPRINT_NAME,
            "required_mode_ids": required_mode_ids_for_site_key("twcaibawang"),
            "known_unavailable_mode_ids": (),
            "blocked_items": TWCAIBAWANG_BLOCKED_ITEMS,
        },
        {
            "name": TWSAIMAHUI_BLUEPRINT_NAME,
            "required_mode_ids": required_mode_ids_for_site_key("twsaimahui"),
            "known_unavailable_mode_ids": TWSAIMAHUI_KNOWN_UNAVAILABLE_MODE_IDS,
            "blocked_items": TWSAIMAHUI_BLOCKED_ITEMS,
        },
        {
            "name": TWJINNIU_BLUEPRINT_NAME,
            "required_mode_ids": required_mode_ids_for_site_key("twjinniu"),
            "known_unavailable_mode_ids": (),
            "blocked_items": TWJINNIU_BLOCKED_ITEMS,
        },
        {
            "name": TWCF888_BLUEPRINT_NAME,
            "required_mode_ids": required_mode_ids_for_site_key("twcf888"),
            "known_unavailable_mode_ids": (),
            "blocked_items": TWCF888_BLOCKED_ITEMS,
        },
        {
            "name": TWSSZ_BLUEPRINT_NAME,
            "required_mode_ids": required_mode_ids_for_site_key("twssz"),
            "known_unavailable_mode_ids": (),
            "blocked_items": (),
        },
        {
            "name": TWBST528_BLUEPRINT_NAME,
            "required_mode_ids": required_mode_ids_for_site_key("twbst528"),
            "known_unavailable_mode_ids": (),
            "blocked_items": (),
        },
        {
            "name": TWJSZ666_BLUEPRINT_NAME,
            "required_mode_ids": required_mode_ids_for_site_key("twjsz666"),
            "known_unavailable_mode_ids": (),
            "blocked_items": (),
        },
    )
    for profile in profiles:
        conn.execute(
            """
            INSERT INTO site_blueprint_profiles (
                blueprint_name,
                required_mode_ids_json,
                known_unavailable_mode_ids_json,
                blocked_items_json,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(blueprint_name) DO UPDATE SET
                required_mode_ids_json = excluded.required_mode_ids_json,
                known_unavailable_mode_ids_json = excluded.known_unavailable_mode_ids_json,
                blocked_items_json = excluded.blocked_items_json,
                updated_at = excluded.updated_at
            """,
            (
                profile["name"],
                json.dumps(list(profile["required_mode_ids"]), ensure_ascii=False),
                json.dumps(list(profile["known_unavailable_mode_ids"]), ensure_ascii=False),
                json.dumps(list(profile["blocked_items"]), ensure_ascii=False),
                now,
                now,
            ),
        )


def _backfill_site_blueprint_names(conn: Any) -> None:
    if not conn.table_exists("managed_sites"):
        return

    conn.execute(
        """
        UPDATE managed_sites
        SET blueprint_name = ?
        WHERE (blueprint_name IS NULL OR blueprint_name = '' OR blueprint_name = ?)
          AND web_id = 4
        """,
        (SHENGSHI8800_BLUEPRINT_NAME, DEFAULT_SITE_BLUEPRINT_NAME),
    )
    conn.execute(
        """
        UPDATE managed_sites
        SET blueprint_name = ?
        WHERE (blueprint_name IS NULL OR blueprint_name = '' OR blueprint_name = ?)
          AND web_id = 5
        """,
        (TWCAIBAWANG_BLUEPRINT_NAME, DEFAULT_SITE_BLUEPRINT_NAME),
    )
    conn.execute(
        """
        UPDATE managed_sites
        SET blueprint_name = ?
        WHERE (blueprint_name IS NULL OR blueprint_name = '' OR blueprint_name = ?)
          AND web_id = 6
        """,
        (TWSAIMAHUI_BLUEPRINT_NAME, DEFAULT_SITE_BLUEPRINT_NAME),
    )
    conn.execute(
        """
        UPDATE managed_sites
        SET blueprint_name = ?
        WHERE (blueprint_name IS NULL OR blueprint_name = '' OR blueprint_name = ?)
          AND web_id = 7
        """,
        (TWJINNIU_BLUEPRINT_NAME, DEFAULT_SITE_BLUEPRINT_NAME),
    )
    conn.execute(
        """
        UPDATE managed_sites
        SET blueprint_name = ?
        WHERE (blueprint_name IS NULL OR blueprint_name = '' OR blueprint_name = ?)
          AND web_id = 8
        """,
        (TWCF888_BLUEPRINT_NAME, DEFAULT_SITE_BLUEPRINT_NAME),
    )
    conn.execute(
        """
        UPDATE managed_sites
        SET blueprint_name = ?
        WHERE blueprint_name IS NULL OR blueprint_name = ''
        """,
        (DEFAULT_SITE_BLUEPRINT_NAME,),
    )


def ensure_prediction_tables(conn: Any, pk_sql: str) -> None:
    """创建预测相关表：site_prediction_modules、mechanism_status。"""
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS site_prediction_modules (
            {pk_sql},
            site_id INTEGER NOT NULL,
            mechanism_key TEXT NOT NULL,
            mode_id INTEGER,
            status INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(site_id, mechanism_key),
            FOREIGN KEY (site_id) REFERENCES managed_sites(id) ON DELETE CASCADE
        )
        """
    )
    add_column_if_missing(conn, "site_prediction_modules", "mode_id", "INTEGER")
    add_column_if_missing(conn, "site_prediction_modules", "title", "TEXT")

    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS site_blueprint_profiles (
            blueprint_name TEXT PRIMARY KEY,
            required_mode_ids_json TEXT NOT NULL,
            known_unavailable_mode_ids_json TEXT NOT NULL,
            blocked_items_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    add_column_if_missing(conn, "managed_sites", "blueprint_name", "TEXT")
    _seed_site_blueprint_profiles(conn)
    _backfill_site_blueprint_names(conn)

    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS mechanism_status (
            mechanism_key TEXT PRIMARY KEY,
            status INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL
        )
        """
    )

    # Internal-only future-generation bookkeeping. A site may reserve only one
    # candidate per issue/mode; cross-site prefix diversity is best-effort.
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS prediction_generation_controls (
            {pk_sql},
            lottery_type_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            term INTEGER NOT NULL,
            mode_id INTEGER NOT NULL,
            web_id INTEGER NOT NULL,
            rule_id TEXT NOT NULL,
            rule_revision INTEGER NOT NULL,
            target_hit INTEGER NOT NULL,
            verified_hit INTEGER NOT NULL,
            signature_hash TEXT NOT NULL,
            prefix_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(lottery_type_id, year, term, mode_id, web_id)
        )
        """
    )
