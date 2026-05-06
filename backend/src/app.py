"""Lightweight backend API and CMS for lottery data management.

本服务只依赖 Python 标准库，直接复用现有预测、抓取、归一化和文本映射模块。
适合当前项目这种强依赖本地 SQLite 的业务形态，避免为了简单后台管理额外引入
一整套通用 CMS 框架。
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import mimetypes
import os
import secrets
import sys
import traceback
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


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

DEFAULT_POSTGRES_DSN = _cfg_db.get("default_postgres_dsn",
    "postgresql://postgres:2225427@localhost:5432/liuhecai")
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

from common import DEFAULT_TARGET_HIT_RATE, predict  # noqa: E402
from data_fetch import (  # noqa: E402
    DEFAULT_TOKEN,
    MODES_DATA_URL,
    WEB_MANAGE_URL_TEMPLATE,
    ensure_fetch_tables,
    fetch_all_data_for_mode,
    fetch_web_id_list,
    save_mode_all_data,
)
from mechanisms import get_prediction_config, list_prediction_configs  # noqa: E402
from normalize_sqlite import normalize_payload_tables  # noqa: E402
from build_text_history_mappings import build_text_history_mappings  # noqa: E402
from db import auto_increment_primary_key, connect as db_connect, detect_database_engine, quote_identifier  # noqa: E402
from crawler_service import (  # noqa: E402
    CrawlerScheduler,
    import_taiwan_json,
    run_hk_crawler,
    run_macau_crawler,
)


def default_db_target() -> str:
    """Prefer an explicit database URL, then the configured PostgreSQL DSN, then SQLite."""
    return (
        os.environ.get("LOTTERY_DB_PATH")
        or os.environ.get("DATABASE_URL")
        or DEFAULT_POSTGRES_DSN
        or str(DEFAULT_SQLITE_DB_PATH)
    )


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def connect(db_path: str | Path) -> Any:
    return db_connect(db_path)


def row_to_dict(row: Any | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def parse_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on", "是", "启用"}


def hash_password(password: str, salt: str | None = None) -> str:
    """使用 PBKDF2 保存管理员密码，避免明文密码进入 SQLite。

    这里不引入第三方认证框架，密码格式固定为
    `pbkdf2_sha256$iterations$salt$hash`，后续迁移到其他框架时也容易转换。
    """
    if not password:
        raise ValueError("密码不能为空")
    iterations = 260_000
    resolved_salt = salt or secrets.token_urlsafe(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        resolved_salt.encode("utf-8"),
        iterations,
    )
    encoded = base64.b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${iterations}${resolved_salt}${encoded}"


def verify_password(password: str, password_hash: str) -> bool:
    """校验管理员密码，兼容当前 PBKDF2 哈希格式。"""
    try:
        algorithm, iterations, salt, expected = password_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    )
    actual = base64.b64encode(digest).decode("ascii")
    return secrets.compare_digest(actual, expected)


def ensure_column(conn: Any, table_name: str, column_name: str, definition: str) -> None:
    """轻量迁移工具：SQLite 旧表缺列时补列，保留既有业务数据。"""
    columns = set(conn.table_columns(table_name))
    if column_name not in columns:
        conn.execute(
            f"ALTER TABLE {quote_identifier(table_name)} "
            f"ADD COLUMN {quote_identifier(column_name)} {definition}"
        )


def ensure_admin_tables(db_path: str | Path) -> None:
    now = utc_now()

    with connect(db_path) as conn:
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
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS site_prediction_modules (
                {pk_sql},
                site_id INTEGER NOT NULL,
                mechanism_key TEXT NOT NULL,
                status INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(site_id, mechanism_key),
                FOREIGN KEY (site_id) REFERENCES managed_sites(id) ON DELETE CASCADE
            )
            """
        )
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
        ensure_column(conn, "legacy_image_assets", "source_key", "TEXT NOT NULL DEFAULT 'legacy-post-list'")
        ensure_column(conn, "legacy_image_assets", "source_pc", "INTEGER")
        ensure_column(conn, "legacy_image_assets", "source_web", "INTEGER")
        ensure_column(conn, "legacy_image_assets", "source_type", "INTEGER")
        ensure_column(conn, "legacy_image_assets", "title", "TEXT")
        ensure_column(conn, "legacy_image_assets", "storage_path", "TEXT")
        ensure_column(conn, "legacy_image_assets", "legacy_upload_path", "TEXT")
        ensure_column(conn, "legacy_image_assets", "cover_image", "TEXT")
        ensure_column(conn, "legacy_image_assets", "mime_type", "TEXT")
        ensure_column(conn, "legacy_image_assets", "file_size", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "legacy_image_assets", "sort_order", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "legacy_image_assets", "enabled", "INTEGER NOT NULL DEFAULT 1")
        ensure_column(conn, "legacy_image_assets", "notes", "TEXT")
        sync_legacy_image_assets(conn)

        if int(conn.execute("SELECT COUNT(*) AS total FROM admin_users").fetchone()["total"] or 0) == 0:
            _cfg_admin = app_config.section("admin")
            _admin_user = str(_cfg_admin.get("username", "admin"))
            _admin_display = str(_cfg_admin.get("display_name", "系统管理员"))
            _admin_pass = str(_cfg_admin.get("password", "admin123"))
            _admin_role = str(_cfg_admin.get("role", "super_admin"))
            conn.execute(
                """
                INSERT INTO admin_users (
                    username, display_name, password_hash, role, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, 1, ?, ?)
                """,
                (_admin_user, _admin_display, hash_password(_admin_pass), _admin_role, now, now),
            )

        # Migrate existing "六合彩" -> "香港彩"; add missing types
        conn.execute("UPDATE lottery_types SET name = ? WHERE name = ?", ("香港彩", "六合彩"))
        for _lt_name, _lt_time in [("澳门彩", "21:00"), ("台湾彩", "20:30")]:
            _exists = conn.execute("SELECT COUNT(*) AS total FROM lottery_types WHERE name = ?", (_lt_name,)).fetchone()["total"]
            if _exists == 0:
                conn.execute(
                    "INSERT INTO lottery_types (name, draw_time, collect_url, status, created_at, updated_at) VALUES (?, ?, '', 1, ?, ?)",
                    (_lt_name, _lt_time, now, now),
                )

        default_lottery_id = conn.execute(
            "SELECT id FROM lottery_types ORDER BY id LIMIT 1"
        ).fetchone()["id"]

        existing = int(
            conn.execute("SELECT COUNT(*) AS total FROM managed_sites").fetchone()["total"] or 0
        )
        if existing == 0:
            _site_name = str(_cfg_site.get("default_site_name", "默认盛世站点"))
            _site_domain = str(_cfg_site.get("default_domain", "admin.shengshi8800.com"))
            _site_url = str(_cfg_site.get("manage_url_template", ""))
            _site_data_url = str(_cfg_site.get("modes_data_url", ""))
            _site_token = str(_cfg_site.get("default_token", ""))
            _site_req_limit = int(_cfg_site.get("request_limit", 250))
            _site_req_delay = float(_cfg_site.get("request_delay", 0.5))
            _site_announcement = str(_cfg_site.get("default_announcement", ""))
            _site_notes = str(_cfg_site.get("default_notes", ""))
            _site_start = int(_cfg_site.get("start_web_id", 1))
            _site_end = int(_cfg_site.get("end_web_id", 10))
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


def sync_legacy_image_assets(conn: Any) -> None:
    """Persist old image file paths and their public legacy URLs into PostgreSQL.

    The old static page reads image URLs through `/api/post/getList` and direct
    `/uploads/image/...` paths. This sync keeps a deterministic mapping between
    the filesystem source in `backend/data/Images` and those legacy URLs.
    """
    if not LEGACY_IMAGES_DIR.exists():
        return

    now = utc_now()
    for sort_order, file_path in enumerate(sorted(LEGACY_IMAGES_DIR.iterdir()), start=1):
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


def public_site(row: Any) -> dict[str, Any]:
    data = dict(row)
    token = data.pop("token", "") or ""
    data["enabled"] = bool(data["enabled"])
    data["token_present"] = bool(token)
    data["token_preview"] = f"{token[:8]}..." if token else ""
    return data


def list_sites(db_path: str | Path) -> list[dict[str, Any]]:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT s.*, l.name AS lottery_name
            FROM managed_sites s
            LEFT JOIN lottery_types l ON l.id = s.lottery_type_id
            ORDER BY s.enabled DESC, s.id ASC
            """
        ).fetchall()
        return [public_site(row) for row in rows]


def get_site(db_path: str | Path, site_id: int, include_secret: bool = False) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT s.*, l.name AS lottery_name
            FROM managed_sites s
            LEFT JOIN lottery_types l ON l.id = s.lottery_type_id
            WHERE s.id = ?
            """,
            (site_id,),
        ).fetchone()
        if not row:
            raise KeyError(f"site_id={site_id} 不存在")
        data = dict(row) if include_secret else public_site(row)
        data["enabled"] = bool(data["enabled"])
        return data


def save_site(db_path: str | Path, payload: dict[str, Any], site_id: int | None = None) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    now = utc_now()
    fields = {
        "name": str(payload.get("name") or "").strip(),
        "domain": str(payload.get("domain") or "").strip(),
        "lottery_type_id": int(payload.get("lottery_type_id") or 1),
        "enabled": 1 if parse_bool(payload.get("enabled"), True) else 0,
        "start_web_id": int(payload.get("start_web_id") or 1),
        "end_web_id": int(payload.get("end_web_id") or payload.get("start_web_id") or 10),
        "manage_url_template": str(payload.get("manage_url_template") or WEB_MANAGE_URL_TEMPLATE).strip(),
        "modes_data_url": str(payload.get("modes_data_url") or MODES_DATA_URL).strip(),
        "request_limit": int(payload.get("request_limit") or 250),
        "request_delay": float(payload.get("request_delay") or 0.5),
        "announcement": str(payload.get("announcement") or "").strip(),
        "notes": str(payload.get("notes") or "").strip(),
    }
    token = payload.get("token")
    if not fields["name"]:
        raise ValueError("站点名称不能为空")
    if fields["start_web_id"] > fields["end_web_id"]:
        raise ValueError("start_web_id 不能大于 end_web_id")
    if "{web_id}" not in fields["manage_url_template"] and "{id}" not in fields["manage_url_template"]:
        raise ValueError("manage_url_template 必须包含 {web_id} 或 {id}")

    with connect(db_path) as conn:
        if site_id is None:
            row = conn.execute(
                """
                INSERT INTO managed_sites (
                    name, domain, lottery_type_id, enabled, start_web_id, end_web_id,
                    manage_url_template, modes_data_url, token, request_limit,
                    request_delay, announcement, notes,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                (
                    fields["name"],
                    fields["domain"],
                    fields["lottery_type_id"],
                    fields["enabled"],
                    fields["start_web_id"],
                    fields["end_web_id"],
                    fields["manage_url_template"],
                    fields["modes_data_url"],
                    str(token or ""),
                    fields["request_limit"],
                    fields["request_delay"],
                    fields["announcement"],
                    fields["notes"],
                    now,
                    now,
                ),
            ).fetchone()
            return public_site(row)

        existing = conn.execute("SELECT token FROM managed_sites WHERE id = ?", (site_id,)).fetchone()
        if not existing:
            raise KeyError(f"site_id={site_id} 不存在")
        resolved_token = str(token) if token not in (None, "") else str(existing["token"] or "")
        row = conn.execute(
            """
            UPDATE managed_sites
            SET name = ?,
                domain = ?,
                lottery_type_id = ?,
                enabled = ?,
                start_web_id = ?,
                end_web_id = ?,
                manage_url_template = ?,
                modes_data_url = ?,
                token = ?,
                request_limit = ?,
                request_delay = ?,
                announcement = ?,
                notes = ?,
                updated_at = ?
            WHERE id = ?
            RETURNING *
            """,
            (
                fields["name"],
                fields["domain"],
                fields["lottery_type_id"],
                fields["enabled"],
                fields["start_web_id"],
                fields["end_web_id"],
                fields["manage_url_template"],
                fields["modes_data_url"],
                resolved_token,
                fields["request_limit"],
                fields["request_delay"],
                fields["announcement"],
                fields["notes"],
                now,
                site_id,
            ),
        ).fetchone()
        return public_site(row)


def delete_site(db_path: str | Path, site_id: int) -> None:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        cur = conn.execute("DELETE FROM managed_sites WHERE id = ?", (site_id,))
        if cur.rowcount == 0:
            raise KeyError(f"site_id={site_id} 不存在")


def public_user(row: Any) -> dict[str, Any]:
    """过滤密码哈希，只向前端返回可展示的管理员信息。"""
    data = dict(row)
    data.pop("password_hash", None)
    data["status"] = bool(data["status"])
    return data


def login_user(db_path: str | Path, username: str, password: str) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM admin_users WHERE username = ? AND status = 1",
            (username,),
        ).fetchone()
        if not row or not verify_password(password, row["password_hash"]):
            raise PermissionError("用户名或密码错误")

        token = secrets.token_urlsafe(32)
        now = utc_now()
        conn.execute(
            "INSERT INTO admin_sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, row["id"], now),
        )
        conn.execute(
            "UPDATE admin_users SET last_login_at = ?, updated_at = ? WHERE id = ?",
            (now, now, row["id"]),
        )
        refreshed = conn.execute("SELECT * FROM admin_users WHERE id = ?", (row["id"],)).fetchone()
        return {"token": token, "user": public_user(refreshed)}


def auth_user_from_token(db_path: str | Path, token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT u.*
            FROM admin_sessions s
            JOIN admin_users u ON u.id = s.user_id
            WHERE s.token = ? AND u.status = 1
            """,
            (token,),
        ).fetchone()
        return public_user(row) if row else None


def ensure_generation_permission(user: dict[str, Any] | None) -> None:
    """只有后台管理员才能主动触发生成预测。"""
    if not user:
        raise PermissionError("未登录或登录已失效")
    role = str(user.get("role") or "").strip().lower()
    if role not in {"admin", "super_admin"}:
        raise PermissionError("当前账号没有主动生成预测数据的权限")


def logout_user(db_path: str | Path, token: str | None) -> None:
    if not token:
        return
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        conn.execute("DELETE FROM admin_sessions WHERE token = ?", (token,))


def list_users(db_path: str | Path) -> list[dict[str, Any]]:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM admin_users ORDER BY id").fetchall()
        return [public_user(row) for row in rows]


def save_user(db_path: str | Path, payload: dict[str, Any], user_id: int | None = None) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    now = utc_now()
    username = str(payload.get("username") or "").strip()
    display_name = str(payload.get("display_name") or username).strip()
    role = str(payload.get("role") or "admin").strip()
    status = 1 if parse_bool(payload.get("status"), True) else 0
    password = str(payload.get("password") or "")
    if not username:
        raise ValueError("管理员用户名不能为空")

    with connect(db_path) as conn:
        if user_id is None:
            if not password:
                raise ValueError("新增管理员必须设置密码")
            row = conn.execute(
                """
                INSERT INTO admin_users (
                    username, display_name, password_hash, role, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                (username, display_name, hash_password(password), role, status, now, now),
            ).fetchone()
            return public_user(row)

        existing = conn.execute("SELECT * FROM admin_users WHERE id = ?", (user_id,)).fetchone()
        if not existing:
            raise KeyError(f"user_id={user_id} 不存在")
        password_hash = hash_password(password) if password else existing["password_hash"]
        row = conn.execute(
            """
            UPDATE admin_users
            SET username = ?,
                display_name = ?,
                password_hash = ?,
                role = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?
            RETURNING *
            """,
            (username, display_name, password_hash, role, status, now, user_id),
        ).fetchone()
        return public_user(row)


def delete_user(db_path: str | Path, user_id: int) -> None:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        total = int(
            conn.execute("SELECT COUNT(*) AS total FROM admin_users WHERE status = 1").fetchone()["total"]
            or 0
        )
        target = conn.execute("SELECT status FROM admin_users WHERE id = ?", (user_id,)).fetchone()
        if not target:
            raise KeyError(f"user_id={user_id} 不存在")
        if total <= 1 and int(target["status"] or 0) == 1:
            raise ValueError("至少保留一个可登录管理员")
        conn.execute("DELETE FROM admin_users WHERE id = ?", (user_id,))


def list_lottery_types(db_path: str | Path) -> list[dict[str, Any]]:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM lottery_types ORDER BY status DESC, id").fetchall()
        return [dict(row) | {"status": bool(row["status"])} for row in rows]


def save_lottery_type(db_path: str | Path, payload: dict[str, Any], lottery_id: int | None = None) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    now = utc_now()
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("彩种名称不能为空")
    draw_time = str(payload.get("draw_time") or "").strip()
    collect_url = str(payload.get("collect_url") or "").strip()
    status = 1 if parse_bool(payload.get("status"), True) else 0
    with connect(db_path) as conn:
        if lottery_id is None:
            row = conn.execute(
                """
                INSERT INTO lottery_types (name, draw_time, collect_url, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                (name, draw_time, collect_url, status, now, now),
            ).fetchone()
        else:
            row = conn.execute(
                """
                UPDATE lottery_types
                SET name = ?, draw_time = ?, collect_url = ?, status = ?, updated_at = ?
                WHERE id = ?
                RETURNING *
                """,
                (name, draw_time, collect_url, status, now, lottery_id),
            ).fetchone()
            if not row:
                raise KeyError(f"lottery_id={lottery_id} 不存在")
        return dict(row) | {"status": bool(row["status"])}


def delete_lottery_type(db_path: str | Path, lottery_id: int) -> None:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "DELETE FROM lottery_types WHERE id = ? RETURNING id", (lottery_id,)
        ).fetchone()
        if not row:
            raise KeyError(f"lottery_id={lottery_id} 不存在")


def list_draws(db_path: str | Path, limit: int = 200) -> list[dict[str, Any]]:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT d.*, l.name AS lottery_name
            FROM lottery_draws d
            JOIN lottery_types l ON l.id = d.lottery_type_id
            ORDER BY d.year DESC, d.term DESC, d.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            dict(row) | {"status": bool(row["status"]), "is_opened": bool(row["is_opened"])}
            for row in rows
        ]


def save_draw(db_path: str | Path, payload: dict[str, Any], draw_id: int | None = None) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    now = utc_now()
    fields = {
        "lottery_type_id": int(payload.get("lottery_type_id") or 1),
        "year": int(payload.get("year") or datetime.now().year),
        "term": int(payload.get("term") or 1),
        "numbers": str(payload.get("numbers") or "").strip(),
        "draw_time": str(payload.get("draw_time") or "").strip(),
        "status": 1 if parse_bool(payload.get("status"), True) else 0,
        "is_opened": 1 if parse_bool(payload.get("is_opened"), False) else 0,
        "next_term": int(payload.get("next_term") or (int(payload.get("term") or 1) + 1)),
    }
    if not fields["numbers"]:
        raise ValueError("开奖号码不能为空")
    with connect(db_path) as conn:
        if draw_id is None:
            row = conn.execute(
                """
                INSERT INTO lottery_draws (
                    lottery_type_id, year, term, numbers, draw_time, status,
                    is_opened, next_term, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                (*fields.values(), now, now),
            ).fetchone()
        else:
            row = conn.execute(
                """
                UPDATE lottery_draws
                SET lottery_type_id = ?, year = ?, term = ?, numbers = ?, draw_time = ?,
                    status = ?, is_opened = ?, next_term = ?, updated_at = ?
                WHERE id = ?
                RETURNING *
                """,
                (*fields.values(), now, draw_id),
            ).fetchone()
            if not row:
                raise KeyError(f"draw_id={draw_id} 不存在")
        return dict(row) | {"status": bool(row["status"]), "is_opened": bool(row["is_opened"])}


def delete_draw(db_path: str | Path, draw_id: int) -> None:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        cur = conn.execute("DELETE FROM lottery_draws WHERE id = ?", (draw_id,))
        if cur.rowcount == 0:
            raise KeyError(f"draw_id={draw_id} 不存在")


def list_numbers(db_path: str | Path, limit: int = 300, keyword: str = "") -> list[dict[str, Any]]:
    """号码管理直接读取 fixed_data 单表，保持和预测映射同源。"""
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        params: list[Any] = []
        where = ""
        if keyword:
            where = "WHERE name LIKE ? OR sign LIKE ? OR code LIKE ?"
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        rows = conn.execute(
            f"""
            SELECT id, name, code, sign AS category_key, year, status, type, xu
            FROM fixed_data
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
        return [dict(row) | {"status": bool(row["status"])} for row in rows]


def update_number(db_path: str | Path, number_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            UPDATE fixed_data
            SET name = ?,
                code = ?,
                sign = ?,
                year = ?,
                status = ?
            WHERE id = ?
            RETURNING id, name, code, sign AS category_key, year, status, type, xu
            """,
            (
                str(payload.get("name") or "").strip(),
                str(payload.get("code") or "").strip(),
                str(payload.get("category_key") or payload.get("sign") or "").strip(),
                str(payload.get("year") or "").strip(),
                1 if parse_bool(payload.get("status"), True) else 0,
                number_id,
            ),
        ).fetchone()
        if not row:
            raise KeyError(f"number_id={number_id} 不存在")
        return dict(row) | {"status": bool(row["status"])}


def create_number(db_path: str | Path, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            INSERT INTO fixed_data (name, code, sign, year, status, type, xu)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING id, name, code, sign AS category_key, year, status, type, xu
            """,
            (
                str(payload.get("name") or "").strip(),
                str(payload.get("code") or "").strip(),
                str(payload.get("category_key") or payload.get("sign") or "").strip(),
                str(payload.get("year") or "").strip(),
                1 if parse_bool(payload.get("status"), True) else 0,
                int(payload.get("type", 0)),
                int(payload.get("xu", 0)),
            ),
        ).fetchone()
        return dict(row) | {"status": bool(row["status"])}


def delete_number(db_path: str | Path, number_id: int) -> None:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "DELETE FROM fixed_data WHERE id = ? RETURNING id", (number_id,)
        ).fetchone()
        if not row:
            raise KeyError(f"number_id={number_id} 不存在")


def list_site_prediction_modules(db_path: str | Path, site_id: int) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    available = list_prediction_configs()
    available_by_key = {item["key"]: item for item in available}
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM site_prediction_modules
            WHERE site_id = ?
            ORDER BY sort_order, id
            """,
            (site_id,),
        ).fetchall()
    configured: list[dict[str, Any]] = []
    for row in rows:
        data = dict(row) | {"status": bool(row["status"])}
        meta = available_by_key.get(data["mechanism_key"])
        if meta:
            data["title"] = meta["title"]
            data["default_modes_id"] = meta["default_modes_id"]
            data["default_table"] = meta["default_table"]
        configured.append(data)
    configured_keys = {row["mechanism_key"] for row in configured}
    return {
        "site": get_site(db_path, site_id),
        "modules": configured,
        "available_mechanisms": [
            item | {"configured": item["key"] in configured_keys}
            for item in available
        ],
    }


def add_site_prediction_module(db_path: str | Path, site_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    mechanism_key = str(payload.get("mechanism_key") or "").strip()
    if not mechanism_key:
        raise ValueError("预测模块 key 不能为空")
    get_prediction_config(mechanism_key)
    now = utc_now()
    with connect(db_path) as conn:
        row = conn.execute(
            """
            INSERT INTO site_prediction_modules (
                site_id, mechanism_key, status, sort_order, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(site_id, mechanism_key) DO UPDATE SET
                status = excluded.status,
                sort_order = excluded.sort_order,
                updated_at = excluded.updated_at
            RETURNING *
            """,
            (
                site_id,
                mechanism_key,
                1 if parse_bool(payload.get("status"), True) else 0,
                int(payload.get("sort_order") or 0),
                now,
                now,
            ),
        ).fetchone()
        return dict(row) | {"status": bool(row["status"])}


def update_site_prediction_module(
    db_path: str | Path,
    site_id: int,
    module_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """更新站点模块的启用状态和排序，供后台显隐与位置管理使用。"""
    ensure_admin_tables(db_path)
    now = utc_now()
    with connect(db_path) as conn:
        existing = conn.execute(
            "SELECT * FROM site_prediction_modules WHERE site_id = ? AND id = ?",
            (site_id, module_id),
        ).fetchone()
        if not existing:
            raise KeyError(f"module_id={module_id} 不存在")

        status = 1 if parse_bool(payload.get("status"), bool(existing["status"])) else 0
        sort_order = int(payload.get("sort_order") or existing["sort_order"] or 0)
        row = conn.execute(
            """
            UPDATE site_prediction_modules
            SET status = ?,
                sort_order = ?,
                updated_at = ?
            WHERE site_id = ? AND id = ?
            RETURNING *
            """,
            (status, sort_order, now, site_id, module_id),
        ).fetchone()
        return dict(row) | {"status": bool(row["status"])}


def delete_site_prediction_module(db_path: str | Path, site_id: int, module_id: int) -> None:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        cur = conn.execute(
            "DELETE FROM site_prediction_modules WHERE site_id = ? AND id = ?",
            (site_id, module_id),
        )
        if cur.rowcount == 0:
            raise KeyError(f"module_id={module_id} 不存在")


def run_site_prediction_module(db_path: str | Path, site_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """站点数据管理中执行预测模块，机制和历史数据均来自 mechanisms.py。"""
    get_site(db_path, site_id)
    mechanism_key = str(payload.get("mechanism_key") or "").strip()
    if not mechanism_key:
        raise ValueError("预测模块 key 不能为空")
    config = get_prediction_config(mechanism_key)
    return predict(
        config=config,
        res_code=payload.get("res_code"),
        content=payload.get("content"),
        source_table=payload.get("source_table"),
        db_path=db_path,
        target_hit_rate=float(payload.get("target_hit_rate") or DEFAULT_TARGET_HIT_RATE),
    )


def split_csv(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def extract_special_result(row: dict[str, Any]) -> dict[str, Any]:
    """从历史记录中提取特码号、生肖和波色，供前端公开页展示开奖号。"""
    codes = split_csv(row.get("res_code"))
    zodiacs = split_csv(row.get("res_sx"))
    colors = split_csv(row.get("res_color"))
    index = len(codes) - 1
    if index < 0:
        return {"code": "", "zodiac": "", "color": ""}
    return {
        "code": codes[index],
        "zodiac": zodiacs[index] if index < len(zodiacs) else "",
        "color": colors[index] if index < len(colors) else "",
    }


def color_name_to_key(value: str) -> str:
    lowered = str(value or "").strip().lower()
    if lowered in {"red", "blue", "green"}:
        return lowered
    mapping = {
        "红": "red",
        "红波": "red",
        "red波": "red",
        "蓝": "blue",
        "蓝波": "blue",
        "blue波": "blue",
        "绿": "green",
        "绿波": "green",
        "green波": "green",
    }
    return mapping.get(str(value or "").strip(), "red")


def summarize_prediction_text(row: dict[str, Any]) -> str:
    """把不同玩法的历史字段归一成可读文本，避免前端猜测每张源表的结构。"""
    if row.get("content"):
        return str(row["content"])
    xiao_values = [str(row.get("xiao_1") or "").strip(), str(row.get("xiao_2") or "").strip()]
    joined_xiao = " / ".join(value for value in xiao_values if value)
    if joined_xiao:
        return joined_xiao
    for key in ("title", "jiexi", "code", "start", "end"):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def serialize_public_history_row(row: dict[str, Any]) -> dict[str, Any]:
    special = extract_special_result(row)
    issue = f"{row.get('year') or ''}{row.get('term') or ''}".strip()
    return {
        "issue": issue,
        "year": str(row.get("year") or ""),
        "term": str(row.get("term") or ""),
        "prediction_text": summarize_prediction_text(row),
        "result_text": (
            f"{special['zodiac']}{special['code']}".strip() if special["code"] else "待开奖"
        ),
        "is_opened": bool(special["code"]),
        "source_web_id": row.get("web_id"),
        "raw": row,
    }


def load_public_module_history(
    db_path: str | Path,
    mechanism_key: str,
    history_limit: int,
) -> dict[str, Any]:
    """读取模块现有历史记录，不重新生成预测数据。"""
    config = get_prediction_config(mechanism_key)
    with connect(db_path) as conn:
        if not conn.table_exists(config.default_table):
            return {
                "mechanism_key": config.key,
                "title": config.title,
                "default_modes_id": config.default_modes_id,
                "default_table": config.default_table,
                "history": [],
            }

        rows = conn.execute(
            f"""
            SELECT *
            FROM {quote_identifier(config.default_table)}
            ORDER BY CAST(year AS INTEGER) DESC,
                     CAST(term AS INTEGER) DESC,
                     CAST(
                         COALESCE(NULLIF(CAST(source_record_id AS TEXT), ''), CAST(id AS TEXT))
                         AS INTEGER
                     ) DESC
            LIMIT ?
            """,
            (history_limit,),
        ).fetchall()

    return {
        "mechanism_key": config.key,
        "title": config.title,
        "default_modes_id": config.default_modes_id,
        "default_table": config.default_table,
        "history": [serialize_public_history_row(dict(row)) for row in rows],
    }


def resolve_public_site(db_path: str | Path, site_id: int | None = None, domain: str | None = None) -> dict[str, Any]:
    ensure_admin_tables(db_path)
    if site_id is not None:
        return get_site(db_path, site_id)

    normalized_domain = str(domain or "").strip().lower()
    with connect(db_path) as conn:
        if normalized_domain:
            row = conn.execute(
                """
                SELECT s.*, l.name AS lottery_name
                FROM managed_sites s
                LEFT JOIN lottery_types l ON l.id = s.lottery_type_id
                WHERE LOWER(COALESCE(s.domain, '')) = ?
                  AND s.enabled = 1
                ORDER BY s.id
                LIMIT 1
                """,
                (normalized_domain,),
            ).fetchone()
            if row:
                data = public_site(row)
                data["enabled"] = bool(data["enabled"])
                return data

        row = conn.execute(
            """
            SELECT s.*, l.name AS lottery_name
            FROM managed_sites s
            LEFT JOIN lottery_types l ON l.id = s.lottery_type_id
            WHERE s.enabled = 1
            ORDER BY s.id
            LIMIT 1
            """
        ).fetchone()
        if not row:
            raise KeyError("未找到可展示的站点配置")
        data = public_site(row)
        data["enabled"] = bool(data["enabled"])
        return data


def load_public_draw_snapshot(
    db_path: str | Path,
    site: dict[str, Any],
    mechanism_keys: list[str],
) -> dict[str, Any]:
    """公开页最新开奖号来自当前站点已启用模块的历史表，不触发新的预测生成。"""
    latest_row: dict[str, Any] | None = None

    with connect(db_path) as conn:
        for mechanism_key in mechanism_keys:
            config = get_prediction_config(mechanism_key)
            if not conn.table_exists(config.default_table):
                continue
            row = conn.execute(
                f"""
                SELECT web_id, year, term, res_code, res_sx, res_color
                FROM {quote_identifier(config.default_table)}
                WHERE res_code IS NOT NULL
                  AND res_code != ''
                  AND web_id BETWEEN ? AND ?
                ORDER BY CAST(year AS INTEGER) DESC,
                         CAST(term AS INTEGER) DESC,
                         CAST(
                             COALESCE(NULLIF(CAST(source_record_id AS TEXT), ''), CAST(id AS TEXT))
                             AS INTEGER
                         ) DESC
                LIMIT 1
                """,
                (int(site["start_web_id"]), int(site["end_web_id"])),
            ).fetchone()
            if not row:
                continue

            data = dict(row)
            if latest_row is None or (
                int(data.get("year") or 0),
                int(data.get("term") or 0),
            ) > (
                int(latest_row.get("year") or 0),
                int(latest_row.get("term") or 0),
            ):
                latest_row = data

    if latest_row is None:
        return {
            "current_issue": "",
            "result_balls": [],
            "special_ball": None,
        }

    codes = split_csv(latest_row.get("res_code"))
    zodiacs = split_csv(latest_row.get("res_sx"))
    colors = split_csv(latest_row.get("res_color"))
    balls = []
    for index, code in enumerate(codes):
        balls.append(
            {
                "value": code,
                "zodiac": zodiacs[index] if index < len(zodiacs) else "",
                "color": color_name_to_key(colors[index] if index < len(colors) else ""),
            }
        )

    return {
        "current_issue": f"{latest_row.get('year') or ''}{latest_row.get('term') or ''}",
        "result_balls": balls[:-1],
        "special_ball": balls[-1] if balls else None,
    }


def get_public_site_page_data(
    db_path: str | Path,
    *,
    site_id: int | None = None,
    domain: str | None = None,
    history_limit: int = 8,
) -> dict[str, Any]:
    """公开页数据按站点模块配置读取历史记录，不在这里主动生成预测。"""
    site = resolve_public_site(db_path, site_id=site_id, domain=domain)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM site_prediction_modules
            WHERE site_id = ?
              AND status = 1
            ORDER BY sort_order, id
            """,
            (int(site["id"]),),
        ).fetchall()

    modules = []
    for row in rows:
        module_meta = load_public_module_history(
            db_path,
            str(row["mechanism_key"]),
            history_limit,
        )
        modules.append(
            {
                "id": int(row["id"]),
                "mechanism_key": str(row["mechanism_key"]),
                "sort_order": int(row["sort_order"] or 0),
                "status": bool(row["status"]),
                **module_meta,
            }
        )

    mechanism_keys = [str(row["mechanism_key"]) for row in rows]

    return {
        "site": site,
        "draw": load_public_draw_snapshot(db_path, site, mechanism_keys),
        "modules": modules,
    }


def list_legacy_post_images(
    db_path: str | Path,
    *,
    source_pc: int | None = None,
    source_web: int | None = None,
    source_type: int | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return old page image cards using stored PostgreSQL path mappings.

    We only expose persisted rows here. If a mapping is missing, the sync step in
    `ensure_admin_tables` is responsible for repairing it from disk.
    """
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        clauses = ["enabled = 1", "source_key = ?"]
        params: list[Any] = ["legacy-post-list"]

        if source_pc is not None:
            clauses.append("source_pc = ?")
            params.append(source_pc)
        if source_web is not None:
            clauses.append("source_web = ?")
            params.append(source_web)
        if source_type is not None:
            clauses.append("source_type = ?")
            params.append(source_type)

        params.append(max(1, int(limit)))
        rows = conn.execute(
            f"""
            SELECT id, title, file_name, storage_path, legacy_upload_path, cover_image,
                   mime_type, file_size, sort_order, enabled
            FROM legacy_image_assets
            WHERE {' AND '.join(clauses)}
            ORDER BY sort_order, id
            LIMIT ?
            """,
            params,
        ).fetchall()

    return [dict(row) for row in rows]


def get_legacy_current_term(db_path: str | Path, lottery_type_id: int = 1) -> dict[str, Any]:
    """旧静态页会先读取当前已开奖期号，再自行推导下一预测期。"""
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT year, term, next_term
            FROM lottery_draws
            WHERE lottery_type_id = ?
              AND is_opened = 1
            ORDER BY year DESC, term DESC, id DESC
            LIMIT 1
            """,
            (lottery_type_id,),
        ).fetchone()
        if row:
            data = dict(row)
            current_term = int(data.get("term") or 0)
            next_term = data.get("next_term") or (current_term + 1 if current_term else "")
            return {
                "lottery_type_id": lottery_type_id,
                "term": str(data.get("term") or ""),
                "issue": f"{data.get('year') or ''}{data.get('term') or ''}",
                "next_term": str(next_term or ""),
            }

        # 旧库迁移后如果还没补 lottery_draws，也允许从历史预测表回退推导当前期号。
        # 这里选用旧前台确实展示的常用玩法表，优先找到任意一条已开奖记录。
        fallback_modes = (43, 38, 46, 50)
        for modes_id in fallback_modes:
            meta = conn.execute(
                """
                SELECT table_name
                FROM mode_payload_tables
                WHERE modes_id = ?
                LIMIT 1
                """,
                (modes_id,),
            ).fetchone()
            if not meta:
                continue

            table_name = str(meta["table_name"])
            if not conn.table_exists(table_name):
                continue

            legacy_row = conn.execute(
                f"""
                SELECT year, term
                FROM {quote_identifier(table_name)}
                WHERE res_code IS NOT NULL
                  AND res_code != ''
                ORDER BY CAST(year AS INTEGER) DESC,
                         CAST(term AS INTEGER) DESC,
                         CAST(
                             COALESCE(NULLIF(CAST(source_record_id AS TEXT), ''), CAST(id AS TEXT))
                             AS INTEGER
                         ) DESC
                LIMIT 1
                """
            ).fetchone()
            if not legacy_row:
                continue

            year = str(legacy_row["year"] or "")
            term = str(legacy_row["term"] or "")
            next_term = ""
            try:
                next_term = str(int(term) + 1) if term else ""
            except ValueError:
                next_term = ""

            return {
                "lottery_type_id": lottery_type_id,
                "term": term,
                "issue": f"{year}{term}",
                "next_term": next_term,
            }

        return {
            "lottery_type_id": lottery_type_id,
            "term": "",
            "issue": "",
            "next_term": "",
        }


def load_legacy_mode_rows(
    db_path: str | Path,
    *,
    modes_id: int,
    limit: int = 10,
    web: int | None = None,
    type_value: int | None = None,
) -> dict[str, Any]:
    """给旧前端模块提供原始历史表数据，不重建、不生成预测结果。"""
    with connect(db_path) as conn:
        meta = conn.execute(
            """
            SELECT modes_id, title, table_name, record_count
            FROM mode_payload_tables
            WHERE modes_id = ?
            LIMIT 1
            """,
            (modes_id,),
        ).fetchone()
        if not meta:
            raise KeyError(f"modes_id={modes_id} 不存在")

        meta_dict = dict(meta)
        table_name = str(meta_dict["table_name"])
        if not conn.table_exists(table_name):
            return {
                **meta_dict,
                "rows": [],
            }

        columns = set(conn.table_columns(table_name))
        filters: list[str] = []
        params: list[Any] = []

        # 旧静态页的每个模块都带 web/type 参数，同一玩法按来源站点过滤后才符合原展示。
        if web is not None:
            if "web" in columns:
                filters.append("CAST(web AS INTEGER) = ?")
                params.append(web)
            elif "web_id" in columns:
                filters.append("CAST(web_id AS INTEGER) = ?")
                params.append(web)

        if type_value is not None and "type" in columns:
            filters.append("CAST(type AS INTEGER) = ?")
            params.append(type_value)

        where_clause = f" WHERE {' AND '.join(filters)}" if filters else ""

        order_parts: list[str] = []
        if "year" in columns:
            order_parts.append("CAST(year AS INTEGER) DESC")
        if "term" in columns:
            order_parts.append("CAST(term AS INTEGER) DESC")
        if "source_record_id" in columns:
            order_parts.append("CAST(COALESCE(NULLIF(CAST(source_record_id AS TEXT), ''), '0') AS INTEGER) DESC")
        elif "id" in columns:
            order_parts.append("CAST(id AS INTEGER) DESC")
        order_clause = f" ORDER BY {', '.join(order_parts)}" if order_parts else ""

        rows = conn.execute(
            f"""
            SELECT *
            FROM {quote_identifier(table_name)}
            {where_clause}
            {order_clause}
            LIMIT ?
            """,
            (*params, max(1, limit)),
        ).fetchall()

        return {
            **meta_dict,
            "rows": [dict(row) for row in rows],
        }


def create_fetch_run(db_path: str | Path, site_id: int) -> int:
    with connect(db_path) as conn:
        row = conn.execute(
            """
            INSERT INTO site_fetch_runs (site_id, status, message, started_at)
            VALUES (?, 'running', '', ?)
            RETURNING id
            """,
            (site_id, utc_now()),
        ).fetchone()
        return int(row["id"])


def finish_fetch_run(
    db_path: str | Path,
    run_id: int,
    status: str,
    message: str,
    modes_count: int,
    records_count: int,
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE site_fetch_runs
            SET status = ?,
                message = ?,
                modes_count = ?,
                records_count = ?,
                finished_at = ?
            WHERE id = ?
            """,
            (status, message, modes_count, records_count, utc_now(), run_id),
        )


def fetch_site_data(
    db_path: str | Path,
    site_id: int,
    *,
    normalize_after: bool = True,
    build_text_mappings_after: bool = True,
) -> dict[str, Any]:
    """按 CMS 站点配置抓取数据，并可选执行归一化和文本映射刷新。"""
    ensure_admin_tables(db_path)
    site = get_site(db_path, site_id, include_secret=True)
    if not site["enabled"]:
        raise ValueError("该站点已禁用，不能执行抓取")

    run_id = create_fetch_run(db_path, site_id)
    modes_count = 0
    records_count = 0
    try:
        modes_by_web = fetch_web_id_list(
            start_web_id=int(site["start_web_id"]),
            end_web_id=int(site["end_web_id"]),
            url_template=str(site["manage_url_template"]),
            token=str(site.get("token") or "") or None,
        )
        fetched_at = utc_now()
        with connect(db_path) as conn:
            ensure_fetch_tables(conn)
            for web_id in range(int(site["start_web_id"]), int(site["end_web_id"]) + 1):
                for mode in modes_by_web.get(web_id, []):
                    all_data = fetch_all_data_for_mode(
                        web_id=web_id,
                        modes_id=int(mode["modes_id"]),
                        base_url=str(site["modes_data_url"]),
                        token=str(site.get("token") or "") or None,
                        limit=int(site["request_limit"]),
                        request_delay=float(site["request_delay"]),
                    )
                    save_mode_all_data(conn, web_id, mode, all_data, fetched_at)
                    conn.commit()
                    modes_count += 1
                    records_count += len(all_data)

        post_process: dict[str, Any] = {}
        if normalize_after:
            post_process["normalized_tables"] = len(normalize_payload_tables(db_path))
        if build_text_mappings_after:
            post_process["text_mappings"] = build_text_history_mappings(db_path, rebuild=True)

        message = "抓取完成"
        finish_fetch_run(db_path, run_id, "success", message, modes_count, records_count)
        return {
            "run_id": run_id,
            "status": "success",
            "message": message,
            "modes_count": modes_count,
            "records_count": records_count,
            "post_process": post_process,
        }
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        finish_fetch_run(db_path, run_id, "failed", message, modes_count, records_count)
        raise


def list_fetch_runs(db_path: str | Path, limit: int = 20) -> list[dict[str, Any]]:
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT r.*, s.name AS site_name
            FROM site_fetch_runs r
            LEFT JOIN managed_sites s ON s.id = r.site_id
            ORDER BY r.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


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


_ADMIN_STYLE = """
:root{color-scheme:light;--bg:oklch(0.98 0.005 120);--fg:oklch(0.25 0.02 120);--card:oklch(1 0 0);--card-fg:oklch(0.25 0.02 120);--primary:oklch(0.42 0.15 155);--primary-fg:oklch(0.98 0.01 155);--secondary:oklch(0.96 0.01 120);--secondary-fg:oklch(0.25 0.02 120);--muted:oklch(0.55 0.02 120);--border:oklch(0.92 0.01 120);--ring:oklch(0.42 0.15 155);--radius:16px;--accent:oklch(0.55 0.18 155);--danger:#b42318}
*{box-sizing:border-box}
body{margin:0;font-family:"Microsoft YaHei","Segoe UI",sans-serif;background:var(--bg);color:var(--fg);display:flex;min-height:100vh}
.sidebar{width:240px;background:var(--card);border-right:1px solid var(--border);padding:20px 12px;position:fixed;top:0;left:0;height:100vh;overflow-y:auto;z-index:10;flex-shrink:0}
.sidebar .logo{display:flex;align-items:center;gap:10px;padding:0 8px 20px;border-bottom:1px solid var(--border);margin-bottom:12px}
.sidebar .logo-icon{width:36px;height:36px;border-radius:10px;background:var(--primary);color:var(--primary-fg);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:18px}
.sidebar .logo-text{font-weight:600;font-size:15px}
.sidebar .logo-sub{font-size:11px;color:var(--muted)}
.nav-item{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;font-size:14px;cursor:pointer;color:var(--muted);transition:all .15s;margin-bottom:2px;border:none;background:none;width:100%;text-align:left}
.nav-item:hover{background:var(--secondary);color:var(--fg)}
.nav-item.active{background:var(--primary);color:var(--primary-fg);font-weight:500}
.main{flex:1;padding:24px 32px 40px;min-width:0}
.header-bar{display:flex;justify-content:space-between;align-items:center;padding-bottom:16px;border-bottom:1px solid var(--border);margin-bottom:24px}
.header-bar h1{font-size:22px;font-weight:600;margin:0}
.header-bar p{font-size:13px;color:var(--muted);margin:4px 0 0}
.actions{display:flex;gap:8px;align-items:center}
.panel{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:20px;margin-bottom:20px}
.panel h2{font-size:16px;font-weight:600;margin:0 0 16px}
.field{display:grid;gap:4px;font-size:12px;color:var(--muted)}
.field input,.field select,.field textarea{width:100%;border:1px solid var(--border);border-radius:8px;padding:8px 10px;font:inherit;font-size:13px;background:var(--card);color:var(--fg)}
.field textarea{min-height:60px;resize:vertical}
.field input:focus,.field select:focus,.field textarea:focus{outline:none;border-color:var(--ring);box-shadow:0 0 0 2px oklch(0.42 0.15 155 / 0.15)}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{border-bottom:1px solid var(--border);padding:10px 8px;text-align:left;vertical-align:top}
th{color:var(--muted);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;background:var(--secondary)}
.btn{border:1px solid var(--border);background:var(--card);color:var(--fg);padding:7px 14px;border-radius:8px;cursor:pointer;font-size:13px;font-weight:500;transition:all .12s;display:inline-flex;align-items:center;gap:6px}
.btn:hover{background:var(--secondary)}
.btn-primary{background:var(--primary);color:var(--primary-fg);border-color:var(--primary)}
.btn-danger{color:var(--danger);border-color:oklch(0.8 0.1 25)}
.btn-danger:hover{background:oklch(0.95 0.05 25)}
.btn-sm{padding:5px 10px;font-size:12px}
.badge{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600}
.badge-on{background:oklch(0.88 0.12 145);color:oklch(0.25 0.06 145)}
.badge-off{background:oklch(0.92 0.01 120);color:var(--muted)}
.grid-metrics{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}
.metric-card{border:1px solid var(--border);border-radius:12px;padding:16px;text-align:center}
.metric-card .val{font-size:28px;font-weight:700;line-height:1.2}
.metric-card .lbl{font-size:12px;color:var(--muted);margin-top:4px}
.msg{padding:10px 14px;border-radius:8px;margin-bottom:12px;font-size:13px}
.msg-info{background:oklch(0.9 0.05 155 / 0.3);border:1px solid oklch(0.8 0.08 155)}
.msg-error{background:oklch(0.95 0.05 25 / 0.2);border:1px solid oklch(0.8 0.1 25);color:var(--danger)}
pre{white-space:pre-wrap;background:oklch(0.15 0.01 155);color:oklch(0.92 0.01 120);padding:14px;border-radius:10px;max-height:300px;overflow:auto;font-size:12px}
.tab-content{display:none}
.tab-content.active{display:block}
@media(max-width:768px){.sidebar{width:60px;overflow:hidden}.sidebar .logo-text,.sidebar .logo-sub,.nav-item:not(.active){display:none}.main{padding:16px}}
"""

ADMIN_HTML = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>彩票网站数据管理后台</title>
<style>{_ADMIN_STYLE}</style>
</head>
<body>
<div class="sidebar">
  <div class="logo"><div class="logo-icon">彩</div><div><div class="logo-text">彩票软件后台</div><div class="logo-sub">Lottery CMS</div></div></div>
  <button class="nav-item active" onclick="switchTab('dashboard',this)">数据概览</button>
  <button class="nav-item" onclick="switchTab('users',this)">管理员用户</button>
  <button class="nav-item" onclick="switchTab('lotteries',this)">彩种管理</button>
  <button class="nav-item" onclick="switchTab('draws',this)">开奖管理</button>
  <button class="nav-item" onclick="switchTab('sites',this)">站点管理</button>
  <button class="nav-item" onclick="switchTab('numbers',this)">号码管理</button>
  <button class="nav-item" onclick="switchTab('predictions',this)">预测模块</button>
  <button class="nav-item" onclick="switchTab('sitedata',this)">站点数据</button>
</div>
<div class="main">

<div id="tab-dashboard" class="tab-content active">
  <div class="header-bar"><div><h1>数据概览</h1><p>数据库、预测机制和文本历史映射运行概况</p></div><div class="actions"><button class="btn btn-primary btn-sm" onclick="loadDashboard()">刷新</button><button class="btn btn-sm" onclick="runNormalize()">归一化</button><button class="btn btn-sm" onclick="runMappings()">刷新映射</button></div></div>
  <div id="dashboardMsg" class="msg" style="display:none"></div>
  <div id="dashboardMetrics" class="grid-metrics"></div>
  <div class="panel"><h2>操作输出</h2><pre id="dashboardOutput">等待操作</pre></div>
</div>

<div id="tab-users" class="tab-content">
  <div class="header-bar"><div><h1>管理员用户</h1><p>管理后台登录用户</p></div></div>
  <div id="usersMsg" class="msg" style="display:none"></div>
  <div class="panel" style="display:grid;grid-template-columns:360px 1fr;gap:20px">
    <div><h2 id="usersFormTitle">新增管理员</h2>
    <form id="usersForm" onsubmit="return saveUser(event)">
      <input type="hidden" name="id" />
      <div class="field" style="margin-bottom:8px"><label>用户名</label><input name="username" required /></div>
      <div class="field" style="margin-bottom:8px"><label>显示名称</label><input name="display_name" /></div>
      <div class="field" style="margin-bottom:8px"><label>角色</label><input name="role" value="admin" /></div>
      <div class="field" style="margin-bottom:8px"><label>状态</label><select name="status"><option value="1">启用</option><option value="0">停用</option></select></div>
      <div class="field" style="margin-bottom:8px"><label>密码</label><input name="password" type="password" /></div>
      <button class="btn btn-primary btn-sm" type="submit">保存</button> <button class="btn btn-sm" type="button" onclick="resetUserForm()">新建</button>
    </form></div>
    <div style="overflow-x:auto"><table><thead><tr><th>ID</th><th>用户名</th><th>角色</th><th>状态</th><th>操作</th></tr></thead><tbody id="usersTable"></tbody></table></div>
  </div>
</div>

<div id="tab-lotteries" class="tab-content">
  <div class="header-bar"><div><h1>彩种管理</h1><p>设置彩种名称、开奖时间、采集地址和状态</p></div></div>
  <div id="lotteriesMsg" class="msg" style="display:none"></div>
  <div class="panel" style="display:grid;grid-template-columns:400px 1fr;gap:20px">
    <div><h2 id="lotteriesFormTitle">新增彩种</h2>
    <form id="lotteriesForm" onsubmit="return saveLottery(event)">
      <input type="hidden" name="id" />
      <div class="field" style="margin-bottom:8px"><label>彩种名称</label><input name="name" required /></div>
      <div class="field" style="margin-bottom:8px"><label>开奖时间</label><input name="draw_time" placeholder="21:30" /></div>
      <div class="field" style="margin-bottom:8px"><label>采集地址</label><input name="collect_url" /></div>
      <div class="field" style="margin-bottom:8px"><label>状态</label><select name="status"><option value="1">启用</option><option value="0">停用</option></select></div>
      <button class="btn btn-primary btn-sm" type="submit">保存</button> <button class="btn btn-sm" type="button" onclick="resetLotteryForm()">新建</button>
    </form></div>
    <div style="overflow-x:auto"><table><thead><tr><th>ID</th><th>彩种</th><th>开奖时间</th><th>状态</th><th>操作</th></tr></thead><tbody id="lotteriesTable"></tbody></table></div>
  </div>
</div>

<div id="tab-draws" class="tab-content">
  <div class="header-bar"><div><h1>开奖管理</h1><p>维护年份、期数、开奖号码、开奖时间和状态</p></div></div>
  <div id="drawsMsg" class="msg" style="display:none"></div>
  <div class="panel" style="display:grid;grid-template-columns:420px 1fr;gap:20px">
    <div><h2 id="drawsFormTitle">新增开奖记录</h2>
    <form id="drawsForm" onsubmit="return saveDraw(event)">
      <input type="hidden" name="id" />
      <div class="field" style="margin-bottom:8px"><label>彩种</label><select name="lottery_type_id"></select></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
        <div class="field"><label>年份</label><input name="year" type="number" /></div>
        <div class="field"><label>期数</label><input name="term" type="number" /></div>
      </div>
      <div class="field" style="margin-bottom:8px"><label>开奖号码（逗号分隔）</label><input name="numbers" placeholder="02,25,11,33,06,41,01" /></div>
      <div class="field" style="margin-bottom:8px"><label>开奖时间</label><input name="draw_time" /></div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">
        <div class="field"><label>状态</label><select name="status"><option value="1">启用</option><option value="0">停用</option></select></div>
        <div class="field"><label>是否开奖</label><select name="is_opened"><option value="1">已开奖</option><option value="0">未开奖</option></select></div>
        <div class="field"><label>下一期数</label><input name="next_term" type="number" /></div>
      </div>
      <button class="btn btn-primary btn-sm" type="submit">保存</button> <button class="btn btn-sm" type="button" onclick="resetDrawForm()">新建</button>
    </form></div>
    <div style="overflow-x:auto"><table><thead><tr><th>ID</th><th>彩种</th><th>年份</th><th>期数</th><th>号码</th><th>状态</th><th>操作</th></tr></thead><tbody id="drawsTable"></tbody></table></div>
  </div>
</div>

<div id="tab-sites" class="tab-content">
  <div class="header-bar"><div><h1>站点管理</h1><p>维护站点配置、采集接口和抓取操作</p></div></div>
  <div id="sitesMsg" class="msg" style="display:none"></div>
  <div class="panel" style="display:grid;grid-template-columns:440px 1fr;gap:20px">
    <div><h2 id="sitesFormTitle">新增站点</h2>
    <form id="sitesForm" onsubmit="return saveSite(event)">
      <input type="hidden" name="id" />
      <div class="field" style="margin-bottom:8px"><label>站点名称</label><input name="name" required /></div>
      <div class="field" style="margin-bottom:8px"><label>域名</label><input name="domain" /></div>
      <div class="field" style="margin-bottom:8px"><label>彩种</label><select name="lottery_type_id"></select></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
        <div class="field"><label>启用</label><select name="enabled"><option value="1">启用</option><option value="0">停用</option></select></div>
        <div class="field"><label>起始 web_id</label><input name="start_web_id" type="number" /></div>
        <div class="field"><label>结束 web_id</label><input name="end_web_id" type="number" /></div>
        <div class="field"><label>分页 limit</label><input name="request_limit" type="number" /></div>
        <div class="field"><label>请求间隔</label><input name="request_delay" type="number" step="0.1" /></div>
      </div>
      <div class="field" style="margin-bottom:8px"><label>页面地址模板</label><input name="manage_url_template" /></div>
      <div class="field" style="margin-bottom:8px"><label>数据 API 地址</label><input name="modes_data_url" /></div>
      <div class="field" style="margin-bottom:8px"><label>Token</label><input name="token" placeholder="编辑时留空保持原 token" /></div>
      <div class="field" style="margin-bottom:8px"><label>网站公告</label><textarea name="announcement"></textarea></div>
      <div class="field" style="margin-bottom:8px"><label>备注</label><textarea name="notes"></textarea></div>
      <button class="btn btn-primary btn-sm" type="submit">保存</button> <button class="btn btn-sm" type="button" onclick="resetSiteForm()">新建</button>
    </form></div>
    <div style="overflow-x:auto"><table><thead><tr><th>ID</th><th>站点</th><th>域名</th><th>彩种</th><th>状态</th><th>操作</th></tr></thead><tbody id="sitesTable"></tbody></table></div>
  </div>
  <div class="panel"><h2>抓取记录</h2><div style="overflow-x:auto"><table><thead><tr><th>ID</th><th>站点</th><th>状态</th><th>数量</th><th>信息</th></tr></thead><tbody id="runsTable"></tbody></table></div></div>
</div>

<div id="tab-numbers" class="tab-content">
  <div class="header-bar"><div><h1>号码管理</h1><p>fixed_data 映射数据，供预测机制读取</p></div></div>
  <div id="numbersMsg" class="msg" style="display:none"></div>
  <div class="panel" style="display:grid;grid-template-columns:380px 1fr;gap:20px">
    <div><h2 id="numbersFormTitle">修改号码</h2>
    <form id="numbersForm" onsubmit="return saveNumber(event)">
      <input type="hidden" name="id" />
      <div class="field" style="margin-bottom:8px"><label>搜索</label><div style="display:flex;gap:8px"><input id="numbersKeyword" placeholder="名称 / 分类 / 号码" /><button class="btn btn-sm" type="button" onclick="loadNumbers()">搜索</button></div></div>
      <div class="field" style="margin-bottom:8px"><label>名称</label><input name="name" /></div>
      <div class="field" style="margin-bottom:8px"><label>开奖号码</label><textarea name="code"></textarea></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
        <div class="field"><label>分类标识</label><input name="category_key" /></div>
        <div class="field"><label>年份</label><input name="year" /></div>
      </div>
      <div class="field" style="margin-bottom:8px"><label>状态</label><select name="status"><option value="1">启用</option><option value="0">停用</option></select></div>
      <button class="btn btn-primary btn-sm" type="submit">保存</button>
    </form></div>
    <div style="overflow-x:auto"><table><thead><tr><th>ID</th><th>名称</th><th>号码</th><th>分类</th><th>状态</th><th>操作</th></tr></thead><tbody id="numbersTable"></tbody></table></div>
  </div>
</div>

<div id="tab-predictions" class="tab-content">
  <div class="header-bar"><div><h1>预测模块</h1><p>由 mechanisms.py 自动提供的预测机制列表</p></div></div>
  <div class="panel"><div style="overflow-x:auto"><table><thead><tr><th>Key</th><th>标题</th><th>数据表</th></tr></thead><tbody id="predictionsTable"></tbody></table></div></div>
</div>

<div id="tab-sitedata" class="tab-content">
  <div class="header-bar"><div><h1>站点数据管理</h1><p>管理站点预测彩票号码模块</p></div></div>
  <div id="sitedataMsg" class="msg" style="display:none"></div>
  <div class="panel">
    <div style="display:flex;gap:12px;align-items:center"><label style="font-weight:500;font-size:13px">选择站点</label><select id="sitedataSiteSelect" onchange="loadSiteData()" style="flex:1;max-width:300px;border:1px solid var(--border);border-radius:8px;padding:8px 10px;font-size:13px"></select></div>
  </div>
  <div class="panel" id="sitedataPanel" style="display:grid;grid-template-columns:340px 1fr;gap:20px">
    <div><h2>添加预测模块</h2>
    <div style="display:flex;gap:8px;margin-bottom:12px"><select id="sitedataMechanismSelect" style="flex:1;border:1px solid var(--border);border-radius:8px;padding:8px 10px;font-size:13px"></select><button class="btn btn-primary btn-sm" onclick="addSiteModule()">添加</button></div>
    <pre id="sitedataOutput" style="max-height:200px">等待操作</pre></div>
    <div style="overflow-x:auto"><table><thead><tr><th>ID</th><th>模块</th><th>状态</th><th>排序</th><th>操作</th></tr></thead><tbody id="sitedataTable"></tbody></table></div>
  </div>
</div>

</div>

<script>
let _token = localStorage.getItem("liuhecai_admin_token") || ""

function setToken(t) {{ _token = t; localStorage.setItem("liuhecai_admin_token", t) }}
function clearToken() {{ _token = ""; localStorage.removeItem("liuhecai_admin_token") }}

async function api(path, opts = {{}}) {{
  const h = {{ "Content-Type": "application/json", ...(opts.headers || {{}}) }}
  if (_token) h["Authorization"] = "Bearer " + _token
  const res = await fetch(path, {{ ...opts, headers: h }})
  const d = await res.json()
  if (!res.ok) throw new Error(d.error || d.detail || "req failed")
  return d
}}

function esc(v) {{ return String(v ?? "").replace(/[&<>"']/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}})[c]) }}

function badge(v) {{ return v ? "<span class='badge badge-on'>启用</span>" : "<span class='badge badge-off'>停用</span>" }}

function msg(el, text, err) {{ el.style.display = text ? "block" : "none"; el.textContent = text || ""; el.className = "msg " + (err ? "msg-error" : "msg-info") }}

function switchTab(name, btn) {{
  document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"))
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"))
  document.getElementById("tab-" + name).classList.add("active")
  if (btn) btn.classList.add("active")
  const fns = {{users:loadUsers,lotteries:loadLotteries,draws:loadDraws,sites:loadSites,numbers:loadNumbers,predictions:loadPredictions,sitedata:loadSiteData,dashboard:loadDashboard}}
  if (fns[name]) fns[name]()
}}

async function loadDashboard() {{
  try {{
    const d = await api("/api/health")
    document.getElementById("dashboardMetrics").innerHTML = Object.entries(d.summary || {{}}).map(([k,v]) => `<div class="metric-card"><div class="val">${{v}}</div><div class="lbl">${{k}}</div></div>`).join("")
    msg(document.getElementById("dashboardMsg"), "")
  }} catch(e) {{ msg(document.getElementById("dashboardMsg"), e.message, true) }}
}}

async function runNormalize() {{
  try {{ const r = await api("/api/admin/normalize",{{method:"POST"}}); document.getElementById("dashboardOutput").textContent = JSON.stringify(r,null,2); await loadDashboard() }}
  catch(e) {{ document.getElementById("dashboardOutput").textContent = e.message }}
}}

async function runMappings() {{
  try {{ const r = await api("/api/admin/text-mappings",{{method:"POST"}}); document.getElementById("dashboardOutput").textContent = JSON.stringify(r,null,2); await loadDashboard() }}
  catch(e) {{ document.getElementById("dashboardOutput").textContent = e.message }}
}}

async function loadUsers() {{
  try {{
    const d = await api("/api/admin/users"); const el = document.getElementById("usersTable")
    el.innerHTML = (d.users||[]).map(u => `<tr><td>${{u.id}}</td><td><b>${{esc(u.display_name)}}</b><br><span style="color:var(--muted);font-size:12px">${{esc(u.username)}}</span></td><td>${{esc(u.role)}}</td><td>${{badge(u.status)}}</td><td><button class="btn btn-sm" onclick='editUser(${{u.id}},"${{esc(u.username)}}","${{esc(u.display_name||"")}}","${{esc(u.role)}}",${{u.status}})'>修改</button><button class="btn btn-sm btn-danger" onclick="deleteUser(${{u.id}})">删除</button></td></tr>`).join("")
  }} catch(e) {{ msg(document.getElementById("usersMsg"), e.message, true) }}
}}

function editUser(id,uname,dname,role,stat) {{
  document.getElementById("usersFormTitle").textContent = "修改管理员"; const f = document.getElementById("usersForm")
  f.elements.id.value = id; f.elements.username.value = uname; f.elements.display_name.value = dname
  f.elements.role.value = role; f.elements.status.value = stat ? "1" : "0"
  f.elements.password.required = false; f.elements.password.placeholder = "留空不变"
}}

function resetUserForm() {{
  document.getElementById("usersFormTitle").textContent = "新增管理员"
  document.getElementById("usersForm").reset(); document.getElementById("usersForm").elements.id.value = ""
  document.querySelector("#usersForm [name=password]").required = true
  document.querySelector("#usersForm [name=password]").placeholder = ""
}}

async function saveUser(e) {{
  e.preventDefault(); const f = e.target; const id = f.elements.id.value
  const p = {{username:f.elements.username.value,display_name:f.elements.display_name.value,role:f.elements.role.value,status:f.elements.status.value==="1"}}
  if (f.elements.password.value) p.password = f.elements.password.value
  try {{ await api(id?"/api/admin/users/"+id:"/api/admin/users",{{method:id?"PUT":"POST",body:JSON.stringify(p)}}); resetUserForm(); await loadUsers(); msg(document.getElementById("usersMsg"),"保存成功") }}
  catch(e) {{ msg(document.getElementById("usersMsg"), e.message, true) }}
}}

async function deleteUser(id) {{
  if (!confirm("确认删除？")) return
  try {{ await api("/api/admin/users/"+id,{{method:"DELETE"}}); await loadUsers() }} catch(e) {{ msg(document.getElementById("usersMsg"), e.message, true) }}
}}

async function loadLotteries() {{
  try {{
    const d = await api("/api/admin/lottery-types")
    document.getElementById("lotteriesTable").innerHTML = (d.lottery_types||[]).map(r => `<tr><td>${{r.id}}</td><td>${{esc(r.name)}}</td><td>${{esc(r.draw_time||"")}}</td><td>${{badge(r.status)}}</td><td><button class="btn btn-sm" onclick='editLottery(${{r.id}},"${{esc(r.name)}}","${{esc(r.draw_time||"")}}","${{esc(r.collect_url||"")}}",${{r.status}})'>修改</button><button class="btn btn-sm btn-danger" onclick="deleteLottery(${{r.id}})">删除</button></td></tr>`).join("")
  }} catch(e) {{ msg(document.getElementById("lotteriesMsg"), e.message, true) }}
}}

function editLottery(id,name,dt,cu,stat) {{
  document.getElementById("lotteriesFormTitle").textContent = "修改彩种"; const f = document.getElementById("lotteriesForm")
  f.elements.id.value = id; f.elements.name.value = name; f.elements.draw_time.value = dt; f.elements.collect_url.value = cu
  f.elements.status.value = stat ? "1" : "0"
}}

function resetLotteryForm() {{ document.getElementById("lotteriesFormTitle").textContent = "新增彩种"; document.getElementById("lotteriesForm").reset(); document.getElementById("lotteriesForm").elements.id.value = "" }}

async function saveLottery(e) {{
  e.preventDefault(); const f=e.target; const id=f.elements.id.value
  const p={{name:f.elements.name.value,draw_time:f.elements.draw_time.value,collect_url:f.elements.collect_url.value,status:f.elements.status.value==="1"}}
  try {{ await api(id?"/api/admin/lottery-types/"+id:"/api/admin/lottery-types",{{method:id?"PUT":"POST",body:JSON.stringify(p)}}); resetLotteryForm(); await loadLotteries(); msg(document.getElementById("lotteriesMsg"),"保存成功") }}
  catch(e) {{ msg(document.getElementById("lotteriesMsg"), e.message, true) }}
}}

async function deleteLottery(id) {{
  if (!confirm("确认删除？")) return
  try {{ await api("/api/admin/lottery-types/"+id,{{method:"DELETE"}}); await loadLotteries() }} catch(e) {{ msg(document.getElementById("lotteriesMsg"), e.message, true) }}
}}

async function loadDraws() {{
  try {{
    const [dd,ld] = await Promise.all([api("/api/admin/draws"),api("/api/admin/lottery-types")])
    const types = ld.lottery_types||[]; const sel = document.getElementById("drawsForm").elements.lottery_type_id
    sel.innerHTML = types.map(t => `<option value="${{t.id}}">${{esc(t.name)}}</option>`).join("")
    document.getElementById("drawsTable").innerHTML = (dd.draws||[]).map(r => `<tr><td>${{r.id}}</td><td>${{esc(r.lottery_name||"")}}</td><td>${{r.year}}</td><td>${{r.term}}</td><td style="max-width:180px;word-break:break-all">${{esc(r.numbers)}}</td><td>${{badge(r.status)}}</td><td><button class="btn btn-sm" onclick="editDraw(${{r.id}},${{r.lottery_type_id}},${{r.year}},${{r.term}},'${{esc(r.numbers||"")}}','${{esc(r.draw_time||"")}}',${{r.status?1:0}},${{r.is_opened?1:0}},${{r.next_term}})">修改</button><button class="btn btn-sm btn-danger" onclick="deleteDraw(${{r.id}})">删除</button></td></tr>`).join("")
  }} catch(e) {{ msg(document.getElementById("drawsMsg"), e.message, true) }}
}}

function editDraw(id,ltid,year,term,numbers,dt,stat,opened,nt) {{
  document.getElementById("drawsFormTitle").textContent = "修改开奖记录"; const f=document.getElementById("drawsForm")
  f.elements.id.value=id; f.elements.lottery_type_id.value=ltid; f.elements.year.value=year; f.elements.term.value=term; f.elements.numbers.value=numbers; f.elements.draw_time.value=dt; f.elements.status.value=stat?"1":"0"; f.elements.is_opened.value=opened?"1":"0"; f.elements.next_term.value=nt
}}

function resetDrawForm() {{ document.getElementById("drawsFormTitle").textContent = "新增开奖记录"; const f=document.getElementById("drawsForm"); f.reset(); f.elements.id.value=""; f.elements.year.value=new Date().getFullYear(); f.elements.term.value=1; f.elements.next_term.value=2 }}

async function saveDraw(e) {{
  e.preventDefault(); const f=e.target; const id=f.elements.id.value
  const p={{lottery_type_id:Number(f.elements.lottery_type_id.value),year:Number(f.elements.year.value),term:Number(f.elements.term.value),numbers:f.elements.numbers.value,draw_time:f.elements.draw_time.value,status:f.elements.status.value==="1",is_opened:f.elements.is_opened.value==="1",next_term:Number(f.elements.next_term.value)}}
  try {{ await api(id?"/api/admin/draws/"+id:"/api/admin/draws",{{method:id?"PUT":"POST",body:JSON.stringify(p)}}); resetDrawForm(); await loadDraws(); msg(document.getElementById("drawsMsg"),"保存成功") }}
  catch(e) {{ msg(document.getElementById("drawsMsg"), e.message, true) }}
}}

async function deleteDraw(id) {{
  if (!confirm("确认删除？")) return
  try {{ await api("/api/admin/draws/"+id,{{method:"DELETE"}}); await loadDraws() }} catch(e) {{ msg(document.getElementById("drawsMsg"), e.message, true) }}
}}

async function loadSites() {{
  try {{
    const [sd,ld] = await Promise.all([api("/api/admin/sites"),api("/api/admin/lottery-types")])
    const types=ld.lottery_types||[]; const tsel=document.getElementById("sitesForm").elements.lottery_type_id
    tsel.innerHTML = types.map(t => `<option value="${{t.id}}">${{esc(t.name)}}</option>`).join("")
    try {{
      const runs = await api("/api/admin/fetch-runs")
      document.getElementById("runsTable").innerHTML = (runs.runs||[]).map(r => `<tr><td>${{r.id}}</td><td>${{esc(r.site_name||"")}}</td><td>${{esc(r.status)}}</td><td>${{r.modes_count||0}}/${{r.records_count||0}}</td><td>${{esc(r.message||"")}}</td></tr>`).join("") || "<tr><td colspan='5' style='text-align:center;color:var(--muted)'>暂无</td></tr>"
    }} catch(e) {{}}
    document.getElementById("sitesTable").innerHTML = (sd.sites||[]).map(s => `<tr><td>${{s.id}}</td><td><b>${{esc(s.name)}}</b></td><td>${{esc(s.domain||"-")}}</td><td>${{esc(s.lottery_name||"-")}}</td><td>${{badge(s.enabled)}}</td><td><button class="btn btn-sm" onclick="editSite(${{s.id}},'${{esc(s.name)}}','${{esc(s.domain||"")}}',${{s.lottery_type_id||1}},${{s.enabled?1:0}},${{s.start_web_id||1}},${{s.end_web_id||10}},'${{esc(s.manage_url_template||"")}}','${{esc(s.modes_data_url||"")}}',${{s.request_limit||250}},${{s.request_delay||0.5}},'${{esc((s.announcement||"").replace(/'/g,"\\\\'"))}}','${{esc((s.notes||"").replace(/'/g,"\\\\'"))}}',${{s.token_present?1:0}})">修改</button><button class="btn btn-sm btn-primary" onclick="fetchSite(${{s.id}})">抓取</button><button class="btn btn-sm btn-danger" onclick="deleteSite(${{s.id}})">删除</button></td></tr>`).join("") || "<tr><td colspan='6' style='text-align:center;color:var(--muted)'>暂无站点</td></tr>"
  }} catch(e) {{ msg(document.getElementById("sitesMsg"), e.message, true) }}
}}

function editSite(id,name,dom,ltid,enabled,sw,ew,url,dataurl,rl,rd,ann,notes,tp) {{
  document.getElementById("sitesFormTitle").textContent = "修改站点"; const f=document.getElementById("sitesForm")
  f.elements.id.value=id; f.elements.name.value=name; f.elements.domain.value=dom; f.elements.lottery_type_id.value=ltid; f.elements.enabled.value=enabled?"1":"0"; f.elements.start_web_id.value=sw; f.elements.end_web_id.value=ew; f.elements.manage_url_template.value=url; f.elements.modes_data_url.value=dataurl; f.elements.request_limit.value=rl; f.elements.request_delay.value=rd; f.elements.announcement.value=ann; f.elements.notes.value=notes;
  f.elements.token.value=""; f.elements.token.placeholder = tp ? "留空保持原 token" : ""
  window.scrollTo({{top:0,behavior:"smooth"}})
}}

function resetSiteForm() {{ document.getElementById("sitesFormTitle").textContent = "新增站点"; const f=document.getElementById("sitesForm"); f.reset(); f.elements.id.value=""; f.elements.start_web_id.value=1; f.elements.end_web_id.value=10; f.elements.request_limit.value=250; f.elements.request_delay.value=0.5 }}

async function saveSite(e) {{
  e.preventDefault(); const f=e.target; const id=f.elements.id.value
  const p={{name:f.elements.name.value,domain:f.elements.domain.value,lottery_type_id:Number(f.elements.lottery_type_id.value),enabled:f.elements.enabled.value==="1",start_web_id:Number(f.elements.start_web_id.value),end_web_id:Number(f.elements.end_web_id.value),manage_url_template:f.elements.manage_url_template.value,modes_data_url:f.elements.modes_data_url.value,request_limit:Number(f.elements.request_limit.value),request_delay:Number(f.elements.request_delay.value),announcement:f.elements.announcement.value,notes:f.elements.notes.value}}
  if (f.elements.token.value) p.token = f.elements.token.value
  try {{ await api(id?"/api/admin/sites/"+id:"/api/admin/sites",{{method:id?"PUT":"POST",body:JSON.stringify(p)}}); resetSiteForm(); await loadSites(); msg(document.getElementById("sitesMsg"),"保存成功") }}
  catch(e) {{ msg(document.getElementById("sitesMsg"), e.message, true) }}
}}

async function deleteSite(id) {{
  if (!confirm("确认删除？")) return
  try {{ await api("/api/admin/sites/"+id,{{method:"DELETE"}}); await loadSites() }} catch(e) {{ msg(document.getElementById("sitesMsg"), e.message, true) }}
}}

async function fetchSite(id) {{
  try {{ msg(document.getElementById("sitesMsg"),"抓取中..."); await api("/api/admin/sites/"+id+"/fetch",{{method:"POST",body:JSON.stringify({{normalize:true,build_text_mappings:true}})}}); msg(document.getElementById("sitesMsg"),"抓取完成"); await loadSites() }}
  catch(e) {{ msg(document.getElementById("sitesMsg"), e.message, true) }}
}}

async function loadNumbers() {{
  try {{
    const kw=document.getElementById("numbersKeyword").value; const d=await api("/api/admin/numbers?keyword="+encodeURIComponent(kw))
    document.getElementById("numbersTable").innerHTML = (d.numbers||[]).map(r => `<tr><td>${{r.id}}</td><td>${{esc(r.name)}}</td><td style="max-width:260px;word-break:break-all">${{esc(r.code)}}</td><td>${{esc(r.category_key||"")}}</td><td>${{badge(r.status)}}</td><td><button class="btn btn-sm" onclick='editNumber(${{r.id}},"${{esc((r.name||"").replace(/'/g,"\\\\'"))}}","${{esc((r.code||"").replace(/'/g,"\\\\'"))}}","${{esc((r.category_key||"").replace(/'/g,"\\\\'"))}}","${{esc((r.year||"").replace(/'/g,"\\\\'"))}}",${{r.status?1:0}})'>修改</button></td></tr>`).join("") || "<tr><td colspan='6' style='text-align:center;color:var(--muted)'>无结果</td></tr>"
  }} catch(e) {{ msg(document.getElementById("numbersMsg"), e.message, true) }}
}}

function editNumber(id,name,code,ck,year,stat) {{
  document.getElementById("numbersFormTitle").textContent="修改号码"; const f=document.getElementById("numbersForm")
  f.elements.id.value=id; f.elements.name.value=name; f.elements.code.value=code; f.elements.category_key.value=ck; f.elements.year.value=year; f.elements.status.value=stat?"1":"0"
}}

async function saveNumber(e) {{
  e.preventDefault(); const f=e.target; const id=f.elements.id.value; if(!id) return
  const p={{name:f.elements.name.value,code:f.elements.code.value,category_key:f.elements.category_key.value,year:f.elements.year.value,status:f.elements.status.value==="1"}}
  try {{ await api("/api/admin/numbers/"+id,{{method:"PUT",body:JSON.stringify(p)}}); msg(document.getElementById("numbersMsg"),"保存成功"); await loadNumbers() }}
  catch(e) {{ msg(document.getElementById("numbersMsg"), e.message, true) }}
}}

async function loadPredictions() {{
  try {{
    const d=await api("/api/predict/mechanisms")
    document.getElementById("predictionsTable").innerHTML = (d.mechanisms||[]).map(r => `<tr><td><code>${{esc(r.key)}}</code></td><td><b>${{esc(r.title)}}</b></td><td><code>${{esc(r.default_table||"-")}}</code></td></tr>`).join("") || "<tr><td colspan='3' style='text-align:center;color:var(--muted)'>无</td></tr>"
  }} catch(e) {{}}
}}

async function loadSiteData() {{
  try {{
    const sites=await api("/api/admin/sites"); const sel=document.getElementById("sitedataSiteSelect")
    sel.innerHTML=(sites.sites||[]).map(s => `<option value="${{s.id}}">${{esc(s.name)}} (#${{s.id}})</option>`).join("")
    const sid=Number(sel.value); if(!sid) return
    const d=await api("/api/admin/sites/"+sid+"/prediction-modules"); const avail=d.available_mechanisms||[]; const mods=d.modules||[]
    const configured=new Set(mods.map(m=>m.mechanism_key))
    const msel=document.getElementById("sitedataMechanismSelect")
    msel.innerHTML=avail.map(m => `<option value="${{m.key}}" ${{configured.has(m.key)?"disabled":""}}>${{esc(m.title)}} (${{m.key}})</option>`).join("")
    document.getElementById("sitedataTable").innerHTML=mods.map(m => `<tr><td>${{m.id}}</td><td><b>${{esc(m.title||m.mechanism_key)}}</b><br><span style="font-size:12px;color:var(--muted)">${{esc(m.mechanism_key)}}</span></td><td>${{badge(m.status)}}</td><td>${{m.sort_order||0}}</td><td><button class="btn btn-sm" onclick="toggleMod(${{m.id}},${{m.status?0:1}})">${{m.status?"停用":"启用"}}</button><button class="btn btn-sm btn-primary" onclick="runMod('${{m.mechanism_key}}')">执行</button><button class="btn btn-sm btn-danger" onclick="delMod(${{m.id}})">删除</button></td></tr>`).join("") || "<tr><td colspan='5' style='text-align:center;color:var(--muted)'>暂无</td></tr>"
  }} catch(e) {{ msg(document.getElementById("sitedataMsg"), e.message, true) }}
}}

async function addSiteModule() {{
  const sid=Number(document.getElementById("sitedataSiteSelect").value); const key=document.getElementById("sitedataMechanismSelect").value
  if(!sid||!key) return
  try {{ await api("/api/admin/sites/"+sid+"/prediction-modules",{{method:"POST",body:JSON.stringify({{mechanism_key:key,status:true,sort_order:0}})}}); msg(document.getElementById("sitedataMsg"),"已添加"); await loadSiteData() }}
  catch(e) {{ msg(document.getElementById("sitedataMsg"), e.message, true) }}
}}

async function toggleMod(mid,ns) {{
  try {{ await api("/api/admin/sites/"+document.getElementById("sitedataSiteSelect").value+"/prediction-modules/"+mid,{{method:"PATCH",body:JSON.stringify({{status:!!ns}})}}); await loadSiteData() }}
  catch(e) {{ msg(document.getElementById("sitedataMsg"), e.message, true) }}
}}

async function runMod(key) {{
  document.getElementById("sitedataOutput").textContent="执行预测中..."
  try {{
    const r=await api("/api/admin/sites/"+document.getElementById("sitedataSiteSelect").value+"/prediction-modules/run",{{method:"POST",body:JSON.stringify({{mechanism_key:key,target_hit_rate:0.65}})}})
    document.getElementById("sitedataOutput").textContent=JSON.stringify(r,null,2); msg(document.getElementById("sitedataMsg"),"预测完成")
  }} catch(e) {{ msg(document.getElementById("sitedataMsg"), e.message, true) }}
}}

async function delMod(mid) {{
  if(!confirm("确认移除？")) return
  try {{ await api("/api/admin/sites/"+document.getElementById("sitedataSiteSelect").value+"/prediction-modules/"+mid,{{method:"DELETE"}}); await loadSiteData() }}
  catch(e) {{ msg(document.getElementById("sitedataMsg"), e.message, true) }}
}}

if (!_token) {{
  document.getElementById("dashboardMetrics").innerHTML = '<div class="panel"><p>未登录。请先通过 <code>POST /api/auth/login</code> 获取 token，<br>然后执行：<br><code>localStorage.setItem("liuhecai_admin_token", "你的token")</code><br>再刷新页面。</p></div>'
}} else {{
  loadDashboard()
}}
</script>
</body>
</html>"""


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "LiuhecaiBackend/1.0"

    @property
    def db_path(self) -> Path:
        return self.server.db_path  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {self.address_string()} {format % args}")

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        self.dispatch("GET")

    def do_POST(self) -> None:
        self.dispatch("POST")

    def do_PUT(self) -> None:
        self.dispatch("PUT")

    def do_PATCH(self) -> None:
        self.dispatch("PATCH")

    def do_DELETE(self) -> None:
        self.dispatch("DELETE")

    def dispatch(self, method: str) -> None:
        try:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            query = parse_qs(parsed.query)

            if method == "GET" and path == "/":
                self.redirect("/admin")
                return
            if method == "GET" and path == "/admin":
                self.send_html(ADMIN_HTML)
                return
            if method == "GET" and path == "/api/health":
                self.send_json({"ok": True, "summary": database_summary(self.db_path)})
                return
            if method == "POST" and path == "/api/auth/login":
                body = self.read_json()
                self.send_json(
                    login_user(
                        self.db_path,
                        str(body.get("username") or ""),
                        str(body.get("password") or ""),
                    )
                )
                return
            if method == "GET" and path == "/api/auth/me":
                user = auth_user_from_token(self.db_path, self.bearer_token())
                if not user:
                    self.send_error_json(HTTPStatus.UNAUTHORIZED, "未登录或登录已失效")
                    return
                self.send_json({"user": user})
                return
            if method == "POST" and path == "/api/auth/logout":
                logout_user(self.db_path, self.bearer_token())
                self.send_json({"ok": True})
                return
            if method == "GET" and path == "/api/predict/mechanisms":
                self.send_json({"mechanisms": list_prediction_configs()})
                return
            if path.startswith("/api/predict/") and method in {"GET", "POST"}:
                mechanism = path.split("/")[-1]
                body = self.read_json() if method == "POST" else {}
                self.handle_prediction(mechanism, body, query)
                return

            if method == "GET" and path == "/api/public/site-page":
                site_id = query.get("site_id", [None])[0]
                history_limit = int(query.get("history_limit", ["8"])[0])
                self.send_json(
                    get_public_site_page_data(
                        self.db_path,
                        site_id=int(site_id) if site_id not in (None, "") else None,
                        domain=query.get("domain", [None])[0],
                        history_limit=history_limit,
                    )
                )
                return

            if method == "GET" and path == "/api/legacy/current-term":
                lottery_type_id = int(query.get("lottery_type_id", ["1"])[0] or 1)
                self.send_json(get_legacy_current_term(self.db_path, lottery_type_id))
                return

            if method == "GET" and path == "/api/legacy/post-list":
                pc_raw = query.get("pc", [str(LEGACY_POST_LIST_PC)])[0]
                web_raw = query.get("web", [str(LEGACY_POST_LIST_WEB)])[0]
                type_raw = query.get("type", [str(LEGACY_POST_LIST_TYPE)])[0]
                limit = int(query.get("limit", ["20"])[0] or 20)
                self.send_json(
                    {
                        "data": list_legacy_post_images(
                            self.db_path,
                            source_pc=int(pc_raw) if pc_raw not in (None, "") else None,
                            source_web=int(web_raw) if web_raw not in (None, "") else None,
                            source_type=int(type_raw) if type_raw not in (None, "") else None,
                            limit=limit,
                        )
                    }
                )
                return

            if method == "GET" and path == "/api/legacy/module-rows":
                modes_id = int(query.get("modes_id", ["0"])[0] or 0)
                if modes_id <= 0:
                    raise ValueError("modes_id 必须为正整数")
                web_value = query.get("web", [None])[0]
                type_raw = query.get("type", [None])[0]
                limit = int(query.get("limit", ["10"])[0] or 10)
                self.send_json(
                    load_legacy_mode_rows(
                        self.db_path,
                        modes_id=modes_id,
                        limit=limit,
                        web=int(web_value) if web_value not in (None, "") else None,
                        type_value=int(type_raw) if type_raw not in (None, "") else None,
                    )
                )
                return

            if path.startswith("/api/admin/") and not auth_user_from_token(self.db_path, self.bearer_token()):
                self.send_error_json(HTTPStatus.UNAUTHORIZED, "未登录或登录已失效")
                return

            if method == "GET" and path == "/api/admin/users":
                self.send_json({"users": list_users(self.db_path)})
                return
            if method == "POST" and path == "/api/admin/users":
                self.send_json({"user": save_user(self.db_path, self.read_json())}, HTTPStatus.CREATED)
                return
            if path.startswith("/api/admin/users/"):
                user_id = int(path.split("/")[-1])
                if method in {"PUT", "PATCH"}:
                    self.send_json({"user": save_user(self.db_path, self.read_json(), user_id)})
                    return
                if method == "DELETE":
                    delete_user(self.db_path, user_id)
                    self.send_json({"ok": True})
                    return

            if method == "GET" and path == "/api/admin/lottery-types":
                self.send_json({"lottery_types": list_lottery_types(self.db_path)})
                return
            if method == "POST" and path == "/api/admin/lottery-types":
                self.send_json({"lottery_type": save_lottery_type(self.db_path, self.read_json())}, HTTPStatus.CREATED)
                return
            if path.startswith("/api/admin/lottery-types/"):
                lottery_id = int(path.split("/")[-1])
                if method in {"PUT", "PATCH"}:
                    self.send_json({"lottery_type": save_lottery_type(self.db_path, self.read_json(), lottery_id)})
                    return
                if method == "DELETE":
                    delete_lottery_type(self.db_path, lottery_id)
                    self.send_json({"ok": True})
                    return

            if method == "GET" and path == "/api/admin/draws":
                limit = int(query.get("limit", ["200"])[0])
                self.send_json({"draws": list_draws(self.db_path, limit)})
                return
            if method == "POST" and path == "/api/admin/draws":
                self.send_json({"draw": save_draw(self.db_path, self.read_json())}, HTTPStatus.CREATED)
                return
            if path.startswith("/api/admin/draws/"):
                draw_id = int(path.split("/")[-1])
                if method in {"PUT", "PATCH"}:
                    self.send_json({"draw": save_draw(self.db_path, self.read_json(), draw_id)})
                    return
                if method == "DELETE":
                    delete_draw(self.db_path, draw_id)
                    self.send_json({"ok": True})
                    return

            if method == "POST" and path == "/api/admin/crawler/run-hk":
                try:
                    result = run_hk_crawler(self.db_path)
                    self.send_json(result)
                except Exception as e:
                    self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))
                return
            if method == "POST" and path == "/api/admin/crawler/run-macau":
                try:
                    result = run_macau_crawler(self.db_path)
                    self.send_json(result)
                except Exception as e:
                    self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))
                return
            if method == "POST" and path == "/api/admin/crawler/run-all":
                errors = []
                results = {}
                for _label, _fn in [("hk", run_hk_crawler), ("macau", run_macau_crawler)]:
                    try:
                        results[_label] = _fn(self.db_path)
                    except Exception as e:
                        errors.append(f"{_label}: {e}")
                # Also import Taiwan JSON if available
                _taiwan_json = BACKEND_ROOT / "data" / "lottery_data" / "lottery_page_1_20260506_194209.json"
                if _taiwan_json.exists():
                    try:
                        results["taiwan"] = import_taiwan_json(self.db_path, _taiwan_json)
                    except Exception as e:
                        errors.append(f"taiwan: {e}")
                self.send_json({"results": results, "errors": errors if errors else None})
                return
            if method == "POST" and path == "/api/admin/crawler/import-taiwan":
                _taiwan_json = BACKEND_ROOT / "data" / "lottery_data" / "lottery_page_1_20260506_194209.json"
                if not _taiwan_json.exists():
                    self.send_error_json(HTTPStatus.NOT_FOUND, "台湾彩 JSON 数据文件不存在")
                    return
                try:
                    result = import_taiwan_json(self.db_path, _taiwan_json)
                    self.send_json(result)
                except Exception as e:
                    self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))
                return

            if method == "GET" and path == "/api/admin/numbers":
                limit = int(query.get("limit", ["300"])[0])
                keyword = query.get("keyword", [""])[0]
                self.send_json({"numbers": list_numbers(self.db_path, limit, keyword)})
                return
            if method == "POST" and path == "/api/admin/numbers":
                self.send_json({"number": create_number(self.db_path, self.read_json())}, HTTPStatus.CREATED)
                return
            if path.startswith("/api/admin/numbers/"):
                number_id = int(path.split("/")[-1])
                if method in {"PUT", "PATCH"}:
                    self.send_json({"number": update_number(self.db_path, number_id, self.read_json())})
                    return
                if method == "DELETE":
                    delete_number(self.db_path, number_id)
                    self.send_json({"ok": True})
                    return

            if method == "GET" and path == "/api/admin/sites":
                self.send_json({"sites": list_sites(self.db_path)})
                return
            if method == "POST" and path == "/api/admin/sites":
                self.send_json({"site": save_site(self.db_path, self.read_json())}, HTTPStatus.CREATED)
                return
            if method == "GET" and path == "/api/admin/fetch-runs":
                limit = int(query.get("limit", ["20"])[0])
                self.send_json({"runs": list_fetch_runs(self.db_path, limit)})
                return
            if method == "GET" and path == "/api/admin/legacy-images":
                limit = int(query.get("limit", ["50"])[0] or 50)
                self.send_json(
                    {
                        "images": list_legacy_post_images(
                            self.db_path,
                            source_pc=LEGACY_POST_LIST_PC,
                            source_web=LEGACY_POST_LIST_WEB,
                            source_type=LEGACY_POST_LIST_TYPE,
                            limit=limit,
                        )
                    }
                )
                return
            if method == "POST" and path == "/api/admin/normalize":
                result = normalize_payload_tables(self.db_path)
                self.send_json({"normalized_tables": len(result), "tables": result})
                return
            if method == "POST" and path == "/api/admin/text-mappings":
                result = build_text_history_mappings(self.db_path, rebuild=True)
                self.send_json(result)
                return
            if path.startswith("/api/admin/sites/"):
                self.handle_site_detail(method, path)
                return

            self.send_error_json(HTTPStatus.NOT_FOUND, "接口不存在")
        except Exception as exc:
            status = HTTPStatus.BAD_REQUEST
            if isinstance(exc, KeyError):
                status = HTTPStatus.NOT_FOUND
            elif isinstance(exc, PermissionError):
                status = HTTPStatus.FORBIDDEN
            self.send_error_json(status, str(exc), traceback.format_exc())

    def handle_prediction(self, mechanism: str, body: dict[str, Any], query: dict[str, list[str]]) -> None:
        # Active prediction generation mutates operational state expectations even if
        # it does not persist rows directly, so keep this behind the same admin
        # permission boundary as the site-level "run module" action.
        ensure_generation_permission(
            auth_user_from_token(self.db_path, self.bearer_token())
        )

        def pick(name: str, default: Any = None) -> Any:
            if name in body:
                return body[name]
            snake = name.replace("-", "_")
            if snake in body:
                return body[snake]
            return query.get(snake, [default])[0]

        config = get_prediction_config(mechanism)
        result = predict(
            config=config,
            res_code=pick("res_code"),
            content=pick("content"),
            source_table=pick("source_table"),
            db_path=self.db_path,
            target_hit_rate=float(pick("target_hit_rate", DEFAULT_TARGET_HIT_RATE)),
        )
        self.send_json(result)

    def handle_site_detail(self, method: str, path: str) -> None:
        parts = path.split("/")
        if len(parts) < 5:
            self.send_error_json(HTTPStatus.NOT_FOUND, "站点接口不存在")
            return
        site_id = int(parts[4])

        if len(parts) == 5:
            if method == "GET":
                self.send_json({"site": get_site(self.db_path, site_id)})
                return
            if method in {"PUT", "PATCH"}:
                self.send_json({"site": save_site(self.db_path, self.read_json(), site_id)})
                return
            if method == "DELETE":
                delete_site(self.db_path, site_id)
                self.send_json({"ok": True})
                return

        if len(parts) == 6 and parts[5] == "fetch" and method == "POST":
            body = self.read_json()
            result = fetch_site_data(
                self.db_path,
                site_id,
                normalize_after=parse_bool(body.get("normalize"), True),
                build_text_mappings_after=parse_bool(body.get("build_text_mappings"), True),
            )
            self.send_json(result)
            return

        if len(parts) == 6 and parts[5] == "prediction-modules":
            if method == "GET":
                self.send_json(list_site_prediction_modules(self.db_path, site_id))
                return
            if method == "POST":
                self.send_json(
                    {"module": add_site_prediction_module(self.db_path, site_id, self.read_json())},
                    HTTPStatus.CREATED,
                )
                return

        if len(parts) == 7 and parts[5] == "prediction-modules":
            if parts[6] == "run" and method == "POST":
                ensure_generation_permission(
                    auth_user_from_token(self.db_path, self.bearer_token())
                )
                self.send_json(run_site_prediction_module(self.db_path, site_id, self.read_json()))
                return
            if method in {"PUT", "PATCH"}:
                self.send_json(
                    {
                        "module": update_site_prediction_module(
                            self.db_path,
                            site_id,
                            int(parts[6]),
                            self.read_json(),
                        )
                    }
                )
                return
            if method == "DELETE":
                delete_site_prediction_module(self.db_path, site_id, int(parts[6]))
                self.send_json({"ok": True})
                return

        self.send_error_json(HTTPStatus.NOT_FOUND, "站点接口不存在")

    def bearer_token(self) -> str | None:
        header = self.headers.get("Authorization", "")
        if header.lower().startswith("bearer "):
            return header.split(" ", 1)[1].strip()
        return None

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("JSON body 必须是对象")
        return data

    def send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def send_json(self, data: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, text: str) -> None:
        body = text.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: HTTPStatus, message: str, detail: str | None = None) -> None:
        payload = {"ok": False, "error": message}
        if detail:
            payload["detail"] = detail
        self.send_json(payload, status)

    def redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", html.escape(location, quote=True))
        self.end_headers()


def run_server(host: str, port: int, db_path: str | Path) -> None:
    ensure_admin_tables(db_path)
    server = ThreadingHTTPServer((host, port), ApiHandler)
    server.db_path = db_path  # type: ignore[attr-defined]
    print(f"Backend API running at http://{host}:{port}")
    print(f"CMS admin page: http://{host}:{port}/admin")
    print(f"Database engine: {detect_database_engine(db_path)}")
    print(f"Database target: {db_path}")
    # Start background crawler scheduler
    _cfg_crawler = app_config.section("crawler")
    _crawl_interval = int(_cfg_crawler.get("interval_seconds", 3600))
    _scheduler = CrawlerScheduler(db_path, _crawl_interval)
    _scheduler.start()
    try:
        server.serve_forever()
    finally:
        _scheduler.stop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Liuhecai backend API and Python CMS.")
    parser.add_argument("--host", default=os.environ.get("LOTTERY_API_HOST", "127.0.0.1"), help="HTTP host.")
    parser.add_argument("--port", type=int, default=int(os.environ.get("LOTTERY_API_PORT", "8000")), help="HTTP port.")
    parser.add_argument(
        "--db-path",
        default=default_db_target(),
        help="Database target. Accepts a SQLite path or PostgreSQL DSN.",
    )
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    run_server(args.host, args.port, args.db_path)
