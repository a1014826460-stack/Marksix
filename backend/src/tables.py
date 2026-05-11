"""Database table management and bootstrap utilities for the lottery platform.

Provides table creation, schema migration, legacy asset sync, and database
summary functions extracted from the main app module for reuse across the
backend without depending on the HTTP server layer.


彩票平台的数据库表管理和引导工具。
提供从主应用模块中提取的表创建、模式迁移、遗留资产同步和数据库摘要功能，
以便在后端重复使用，而无需依赖HTTP服务器层。
"""

from __future__ import annotations

import mimetypes
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = Path(__file__).resolve().parent
PREDICT_ROOT = SRC_ROOT / "predict"
UTILS_ROOT = SRC_ROOT / "utils"
CRAWLER_ROOT = SRC_ROOT / "crawler"
DEFAULT_SQLITE_DB_PATH = BACKEND_ROOT / "data" / "lottery_modes.sqlite3"

# Load configuration from config.yaml
import config as app_config  # noqa: E402
_cfg_defaults = app_config.load_config()
_cfg_db = _cfg_defaults.get("database", {})
_cfg_site = _cfg_defaults.get("site", {})
_cfg_legacy = _cfg_defaults.get("legacy", {})

DEFAULT_POSTGRES_DSN = _cfg_db.get(
    "default_postgres_dsn",
    "postgresql://postgres:2225427@localhost:5432/liuhecai",
)
LEGACY_IMAGES_DIR = BACKEND_ROOT / _cfg_legacy.get("images_dir", "data/Images")
LEGACY_IMAGES_UPLOAD_BUCKET = _cfg_legacy.get("images_upload_bucket", "20250322")
LEGACY_IMAGES_UPLOAD_PREFIX = f"/uploads/image/{LEGACY_IMAGES_UPLOAD_BUCKET}"
LEGACY_POST_LIST_PC = _cfg_legacy.get("post_list_pc", 305)
LEGACY_POST_LIST_WEB = _cfg_legacy.get("post_list_web", 4)
LEGACY_POST_LIST_TYPE = _cfg_legacy.get("post_list_type", 3)

for path in (PREDICT_ROOT, UTILS_ROOT, CRAWLER_ROOT):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from db import (  # noqa: E402
    auto_increment_primary_key,
    connect,
    detect_database_engine,
    quote_identifier,
    utc_now,
)
from mechanisms import list_prediction_configs  # noqa: E402
from runtime_config import (  # noqa: E402
    ensure_system_config_table,
    get_bootstrap_config_value,
    seed_system_config_defaults,
)

_tables_initialized = False
HK_NAMES = ("香港彩", "六肖彩")
MACAU_NAME = "澳门彩"
TAIWAN_NAME = "台湾彩"


def default_db_target() -> str:
    """Prefer an explicit database URL, then the configured PostgreSQL DSN, then SQLite."""
    return (
        os.environ.get("LOTTERY_DB_PATH")
        or os.environ.get("DATABASE_URL")
        or DEFAULT_POSTGRES_DSN
        or str(DEFAULT_SQLITE_DB_PATH)
    )


def ensure_column(conn: Any, table_name: str, column_name: str, definition: str) -> None:
    """
    deprecated:
    轻量迁移工具：SQLite 旧表缺列时补列，保留既有业务数据。"""
    columns = set(conn.table_columns(table_name))
    if column_name not in columns:
        conn.execute(
            f"ALTER TABLE {quote_identifier(table_name)} "
            f"ADD COLUMN {quote_identifier(column_name)} {definition}"
        )


def sync_legacy_image_assets(conn: Any) -> None:
    """Persist old image file paths and their public legacy URLs into PostgreSQL.

    The old static page reads image URLs through `/api/post/getList` and direct
    `/uploads/image/...` paths. This sync keeps a deterministic mapping between
    the filesystem source in `backend/data/Images` and those legacy URLs.

    将旧的image文件路径及其公共旧版网址保留到PostgreSQL中。
    旧的静态页面通过`/api/post/getList`读取图片URL，并直接指向`/uploads/image/...`路径。
    这种同步保持了`backend/data/Images`中的文件系统源与这些旧URL之间的确定性映射。
    """
    if not LEGACY_IMAGES_DIR.exists():
        return

    now = utc_now()
    for sort_order, file_path in enumerate(
        sorted(LEGACY_IMAGES_DIR.iterdir()), start=1
    ):
        if not file_path.is_file():
            continue

        storage_path = file_path.relative_to(BACKEND_ROOT).as_posix()
        legacy_upload_path = f"{LEGACY_IMAGES_UPLOAD_PREFIX}/{file_path.name}"
        mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        file_size = int(file_path.stat().st_size)
        existing = conn.execute(
            """
            SELECT id
            FROM legacy_image_assets
            WHERE file_name = ?
            """,
            (file_path.name,),
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE legacy_image_assets
                SET source_key = ?,
                    source_pc = ?,
                    source_web = ?,
                    source_type = ?,
                    storage_path = ?,
                    legacy_upload_path = ?,
                    cover_image = ?,
                    mime_type = ?,
                    file_size = ?,
                    sort_order = ?,
                    enabled = 1,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    "legacy-post-list",
                    LEGACY_POST_LIST_PC,
                    LEGACY_POST_LIST_WEB,
                    LEGACY_POST_LIST_TYPE,
                    storage_path,
                    legacy_upload_path,
                    legacy_upload_path,
                    mime_type,
                    file_size,
                    sort_order,
                    now,
                    existing["id"],
                ),
            )
            continue

        conn.execute(
            """
            INSERT INTO legacy_image_assets (
                source_key,
                source_pc,
                source_web,
                source_type,
                file_name,
                storage_path,
                legacy_upload_path,
                cover_image,
                mime_type,
                file_size,
                sort_order,
                enabled,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                "legacy-post-list",
                LEGACY_POST_LIST_PC,
                LEGACY_POST_LIST_WEB,
                LEGACY_POST_LIST_TYPE,
                file_path.name,
                storage_path,
                legacy_upload_path,
                legacy_upload_path,
                mime_type,
                file_size,
                sort_order,
                now,
                now,
            ),
        )


def seed_default_lottery_types(conn: Any, *, now: str) -> None:
    conn.execute(
        "UPDATE lottery_types SET name = ? WHERE name = ?",
        (HK_NAMES[0], HK_NAMES[1]),
    )
    defaults = [
        (
            HK_NAMES[0],
            str(get_bootstrap_config_value("draw.hk_default_draw_time", "21:30")),
            str(get_bootstrap_config_value("draw.hk_default_collect_url", "https://www.lnlllt.com/api.php")),
        ),
        (
            MACAU_NAME,
            str(get_bootstrap_config_value("draw.macau_default_draw_time", "21:00")),
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


def ensure_admin_tables(db_path: str | Path) -> None:
    from auth import hash_password as _hash_password
    from admin.prediction import sync_site_prediction_modules as _sync_modules

    global _tables_initialized

    # 仅在首次调用时执行完整初始化；后续调用只确保连接可用
    if _tables_initialized:
        return
    _tables_initialized = True

    now = utc_now()
    with connect(db_path) as conn:
        ensure_system_config_table(conn)
        seed_system_config_defaults(conn, now=now)
        pk_sql = auto_increment_primary_key("id", conn.engine)
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS managed_sites (
                {pk_sql},
                name TEXT NOT NULL,
                domain TEXT,
                lottery_type_id INTEGER,
                enabled INTEGER NOT NULL DEFAULT 1,
                start_web_id INTEGER NOT NULL DEFAULT 1,
                end_web_id INTEGER NOT NULL DEFAULT 10,
                manage_url_template TEXT NOT NULL,
                modes_data_url TEXT NOT NULL,
                token TEXT,
                request_limit INTEGER NOT NULL DEFAULT 250,
                request_delay REAL NOT NULL DEFAULT 0.5,
                announcement TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (lottery_type_id) REFERENCES lottery_types(id) ON DELETE SET NULL
            )
            """
        )
        ensure_column(conn, "managed_sites", "domain", "TEXT")
        ensure_column(conn, "managed_sites", "lottery_type_id", "INTEGER")
        ensure_column(conn, "managed_sites", "announcement", "TEXT")
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS site_fetch_runs (
                {pk_sql},
                site_id INTEGER,
                status TEXT NOT NULL,
                message TEXT,
                modes_count INTEGER NOT NULL DEFAULT 0,
                records_count INTEGER NOT NULL DEFAULT 0,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                FOREIGN KEY (site_id) REFERENCES managed_sites(id) ON DELETE SET NULL
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS scheduler_tasks (
                {pk_sql},
                task_key TEXT NOT NULL UNIQUE,
                task_type TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{{}}',
                status TEXT NOT NULL DEFAULT 'pending',
                run_at TEXT NOT NULL,
                locked_at TEXT,
                locked_by TEXT,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 3,
                last_error TEXT,
                last_finished_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS admin_users (
                {pk_sql},
                username TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin',
                status INTEGER NOT NULL DEFAULT 1,
                last_login_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                FOREIGN KEY (user_id) REFERENCES admin_users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS lottery_types (
                {pk_sql},
                name TEXT NOT NULL UNIQUE,
                draw_time TEXT,
                collect_url TEXT,
                status INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        ensure_column(conn, "lottery_types", "next_time", "TEXT")
        ensure_column(conn, "lottery_types", "last_auto_task_status", "TEXT")
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS lottery_draws (
                {pk_sql},
                lottery_type_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                term INTEGER NOT NULL,
                numbers TEXT NOT NULL,
                draw_time TEXT,
                status INTEGER NOT NULL DEFAULT 1,
                is_opened INTEGER NOT NULL DEFAULT 0,
                next_term INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(lottery_type_id, year, term),
                FOREIGN KEY (lottery_type_id) REFERENCES lottery_types(id) ON DELETE CASCADE
            )
            """
        )
        ensure_column(conn, "lottery_draws", "next_time", "TEXT")
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
        ensure_column(conn, "site_prediction_modules", "mode_id", "INTEGER")
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS legacy_image_assets (
                {pk_sql},
                source_key TEXT NOT NULL DEFAULT 'legacy-post-list',
                source_pc INTEGER,
                source_web INTEGER,
                source_type INTEGER,
                title TEXT,
                file_name TEXT NOT NULL UNIQUE,
                storage_path TEXT NOT NULL,
                legacy_upload_path TEXT NOT NULL UNIQUE,
                cover_image TEXT NOT NULL UNIQUE,
                mime_type TEXT NOT NULL,
                file_size INTEGER NOT NULL DEFAULT 0,
                sort_order INTEGER NOT NULL DEFAULT 0,
                enabled INTEGER NOT NULL DEFAULT 1,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        ensure_column(
            conn,
            "legacy_image_assets",
            "source_key",
            "TEXT NOT NULL DEFAULT 'legacy-post-list'",
        )
        ensure_column(conn, "legacy_image_assets", "source_pc", "INTEGER")
        ensure_column(conn, "legacy_image_assets", "source_web", "INTEGER")
        ensure_column(conn, "legacy_image_assets", "source_type", "INTEGER")
        ensure_column(conn, "legacy_image_assets", "title", "TEXT")
        ensure_column(conn, "legacy_image_assets", "storage_path", "TEXT")
        ensure_column(conn, "legacy_image_assets", "legacy_upload_path", "TEXT")
        ensure_column(conn, "legacy_image_assets", "cover_image", "TEXT")
        ensure_column(conn, "legacy_image_assets", "mime_type", "TEXT")
        ensure_column(
            conn, "legacy_image_assets", "file_size", "INTEGER NOT NULL DEFAULT 0"
        )
        ensure_column(
            conn, "legacy_image_assets", "sort_order", "INTEGER NOT NULL DEFAULT 0"
        )
        ensure_column(
            conn, "legacy_image_assets", "enabled", "INTEGER NOT NULL DEFAULT 1"
        )
        ensure_column(conn, "legacy_image_assets", "notes", "TEXT")
        sync_legacy_image_assets(conn)
        _sync_modules(conn)
        seed_default_lottery_types(conn, now=now)

        if (
            int(
                conn.execute(
                    "SELECT COUNT(*) AS total FROM admin_users"
                ).fetchone()["total"]
                or 0
            )
            == 0
        ):
            _admin_user = str(get_bootstrap_config_value("admin.username", "admin"))
            _admin_display = str(get_bootstrap_config_value("admin.display_name", "系统管理员"))
            _admin_pass = str(get_bootstrap_config_value("admin.password", "admin123"))
            _admin_role = str(get_bootstrap_config_value("admin.role", "super_admin"))
            conn.execute(
                """
                INSERT INTO admin_users (
                    username, display_name, password_hash, role, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    _admin_user,
                    _admin_display,
                    _hash_password(_admin_pass),
                    _admin_role,
                    now,
                    now,
                ),
            )

        # ──────────────────────────────────────────────────────────
        # 播种彩种数据（确保三种彩种存在）
        # ──────────────────────────────────────────────────────────
        # 将旧的 "六合彩" 统一更名为 "香港彩"
        conn.execute(
            "UPDATE lottery_types SET name = ? WHERE name = ?",
            ("香港彩", "六合彩"),
        )

        # 如果 "香港彩" 不存在则创建，默认采集地址为香港彩官方API
        _hk_exists = conn.execute(
            "SELECT COUNT(*) AS total FROM lottery_types WHERE name = ?",
            ("香港彩",),
        ).fetchone()["total"]
        if _hk_exists == 0:
            conn.execute(
                """
                INSERT INTO lottery_types
                    (name, draw_time, collect_url, status, created_at, updated_at)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (
                    "香港彩",
                    "21:30",
                    "https://www.lnlllt.com/api.php",
                    now,
                    now,
                ),
            )

        # 如果 "澳门彩" 不存在则创建，默认采集地址为澳门彩官方API
        _macau_exists = conn.execute(
            "SELECT COUNT(*) AS total FROM lottery_types WHERE name = ?",
            ("澳门彩",),
        ).fetchone()["total"]
        if _macau_exists == 0:
            conn.execute(
                """
                INSERT INTO lottery_types
                    (name, draw_time, collect_url, status, created_at, updated_at)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (
                    "澳门彩",
                    "21:00",
                    "https://history.macaumarksix.com/history/macaujc2",
                    now,
                    now,
                ),
            )

        # 如果 "台湾彩" 不存在则创建
        # 注意：台湾彩数据来源于本地 JSON 文件导入，不需要线上采集地址（collect_url 留空）
        _tw_exists = conn.execute(
            "SELECT COUNT(*) AS total FROM lottery_types WHERE name = ?",
            ("台湾彩",),
        ).fetchone()["total"]
        if _tw_exists == 0:
            conn.execute(
                """
                INSERT INTO lottery_types
                    (name, draw_time, collect_url, status, created_at, updated_at)
                VALUES (?, ?, '', 1, ?, ?)
                """,
                (
                    "台湾彩",
                    "22:30",
                    now,
                    now,
                ),
            )

        default_lottery_id = conn.execute(
            "SELECT id FROM lottery_types ORDER BY id LIMIT 1"
        ).fetchone()["id"]

        existing = int(
            conn.execute(
                "SELECT COUNT(*) AS total FROM managed_sites"
            ).fetchone()["total"]
            or 0
        )
        if existing == 0:
            _site_name = str(get_bootstrap_config_value("site.default_site_name", "默认盛世站点"))
            _site_domain = str(get_bootstrap_config_value("site.default_domain", "admin.shengshi8800.com"))
            _site_url = str(get_bootstrap_config_value("site.manage_url_template", ""))
            _site_data_url = str(get_bootstrap_config_value("site.modes_data_url", ""))
            _site_token = str(get_bootstrap_config_value("site.default_token", ""))
            _site_req_limit = int(get_bootstrap_config_value("site.request_limit", 250))
            _site_req_delay = float(get_bootstrap_config_value("site.request_delay", 0.5))
            _site_announcement = str(get_bootstrap_config_value("site.default_announcement", ""))
            _site_notes = str(get_bootstrap_config_value("site.default_notes", ""))
            _site_start = int(get_bootstrap_config_value("site.start_web_id", 1))
            _site_end = int(get_bootstrap_config_value("site.end_web_id", 10))
            conn.execute(
                """
                INSERT INTO managed_sites (
                    name, domain, lottery_type_id, enabled, start_web_id, end_web_id,
                    manage_url_template, modes_data_url, token, request_limit, request_delay,
                    announcement, notes,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _site_name,
                    _site_domain,
                    default_lottery_id,
                    _site_start,
                    _site_end,
                    _site_url,
                    _site_data_url,
                    _site_token,
                    _site_req_limit,
                    _site_req_delay,
                    _site_announcement,
                    _site_notes,
                    now,
                    now,
                ),
            )
        else:
            conn.execute(
                "UPDATE managed_sites SET lottery_type_id = COALESCE(lottery_type_id, ?)",
                (default_lottery_id,),
            )
        _sync_modules(conn)


def database_summary(db_path: str | Path) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:

        def count_table(table_name: str) -> int:
            if not conn.table_exists(table_name):
                return 0
            row = conn.execute(
                f"SELECT COUNT(*) AS total FROM {quote_identifier(table_name)}"
            ).fetchone()
            return int(row["total"] or 0)

        return {
            "db_target": str(db_path),
            "db_engine": detect_database_engine(db_path),
            "admin_users": count_table("admin_users"),
            "lottery_types": count_table("lottery_types"),
            "lottery_draws": count_table("lottery_draws"),
            "sites": count_table("managed_sites"),
            "fetched_modes": count_table("fetched_modes"),
            "fetched_mode_records": count_table("fetched_mode_records"),
            "mode_payload_tables": count_table("mode_payload_tables"),
            "text_history_mappings": count_table("text_history_mappings"),
            "site_prediction_modules": count_table("site_prediction_modules"),
            "legacy_image_assets": count_table("legacy_image_assets"),
            "prediction_mechanisms": len(list_prediction_configs()),
        }
