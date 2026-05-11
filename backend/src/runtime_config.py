"""Runtime configuration center with database-first lookup and YAML fallback."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import config as app_config
from db import connect, utc_now

CONFIG_TABLE_NAME = "system_config"


def _bootstrap_section(name: str) -> dict[str, Any]:
    return app_config.section(name) or {}


def _bootstrap_value(section: str, key: str, fallback: Any = None) -> Any:
    return _bootstrap_section(section).get(key, fallback)


CONFIG_DEFAULTS: dict[str, dict[str, Any]] = {
    "database.default_postgres_dsn": {
        "value": _bootstrap_value("database", "default_postgres_dsn", ""),
        "value_type": "string",
        "description": "Bootstrap PostgreSQL DSN for initial startup.",
        "is_secret": 1,
    },
    "admin.username": {
        "value": _bootstrap_value("admin", "username", "admin"),
        "value_type": "string",
        "description": "Bootstrap admin username.",
        "is_secret": 0,
    },
    "admin.password": {
        "value": _bootstrap_value("admin", "password", "admin123"),
        "value_type": "string",
        "description": "Bootstrap admin password.",
        "is_secret": 1,
    },
    "admin.display_name": {
        "value": _bootstrap_value("admin", "display_name", "系统管理员"),
        "value_type": "string",
        "description": "Bootstrap admin display name.",
        "is_secret": 0,
    },
    "admin.role": {
        "value": _bootstrap_value("admin", "role", "super_admin"),
        "value_type": "string",
        "description": "Bootstrap admin role.",
        "is_secret": 0,
    },
    "auth.session_ttl_seconds": {
        "value": _bootstrap_value("auth", "session_ttl_seconds", 86400),
        "value_type": "int",
        "description": "Admin session expiration time in seconds.",
        "is_secret": 0,
    },
    "auth.password_iterations": {
        "value": _bootstrap_value("auth", "password_iterations", 260000),
        "value_type": "int",
        "description": "PBKDF2 password hash iteration count.",
        "is_secret": 0,
    },
    "site.manage_url_template": {
        "value": _bootstrap_value("site", "manage_url_template", ""),
        "value_type": "string",
        "description": "Managed site backend URL template.",
        "is_secret": 0,
    },
    "site.modes_data_url": {
        "value": _bootstrap_value("site", "modes_data_url", ""),
        "value_type": "string",
        "description": "Managed site data API URL.",
        "is_secret": 0,
    },
    "site.default_token": {
        "value": _bootstrap_value("site", "default_token", ""),
        "value_type": "string",
        "description": "Bootstrap managed site token.",
        "is_secret": 1,
    },
    "site.default_site_name": {
        "value": _bootstrap_value("site", "default_site_name", "默认盛世站点"),
        "value_type": "string",
        "description": "Bootstrap managed site name.",
        "is_secret": 0,
    },
    "site.default_domain": {
        "value": _bootstrap_value("site", "default_domain", "admin.shengshi8800.com"),
        "value_type": "string",
        "description": "Bootstrap managed site domain.",
        "is_secret": 0,
    },
    "site.start_web_id": {
        "value": _bootstrap_value("site", "start_web_id", 1),
        "value_type": "int",
        "description": "Bootstrap start web id.",
        "is_secret": 0,
    },
    "site.end_web_id": {
        "value": _bootstrap_value("site", "end_web_id", 10),
        "value_type": "int",
        "description": "Bootstrap end web id.",
        "is_secret": 0,
    },
    "site.request_limit": {
        "value": _bootstrap_value("site", "request_limit", 250),
        "value_type": "int",
        "description": "Default managed site request page size.",
        "is_secret": 0,
    },
    "site.request_delay": {
        "value": _bootstrap_value("site", "request_delay", 0.5),
        "value_type": "float",
        "description": "Default managed site request delay in seconds.",
        "is_secret": 0,
    },
    "site.default_announcement": {
        "value": _bootstrap_value("site", "default_announcement", ""),
        "value_type": "string",
        "description": "Bootstrap managed site announcement.",
        "is_secret": 0,
    },
    "site.default_notes": {
        "value": _bootstrap_value("site", "default_notes", ""),
        "value_type": "string",
        "description": "Bootstrap managed site notes.",
        "is_secret": 0,
    },
    "fetch.user_agent": {
        "value": _bootstrap_value(
            "fetch",
            "user_agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        ),
        "value_type": "string",
        "description": "Default outbound User-Agent.",
        "is_secret": 0,
    },
    "crawler.interval_seconds": {
        "value": _bootstrap_value("crawler", "interval_seconds", 3600),
        "value_type": "int",
        "description": "Legacy crawler interval.",
        "is_secret": 0,
    },
    "crawler.http_timeout_seconds": {
        "value": _bootstrap_value("crawler", "http_timeout_seconds", 30),
        "value_type": "int",
        "description": "Crawler HTTP timeout in seconds.",
        "is_secret": 0,
    },
    "crawler.http_retry_count": {
        "value": _bootstrap_value("crawler", "http_retry_count", 2),
        "value_type": "int",
        "description": "Crawler HTTP retry count.",
        "is_secret": 0,
    },
    "crawler.http_retry_delay_seconds": {
        "value": _bootstrap_value("crawler", "http_retry_delay_seconds", 1.0),
        "value_type": "float",
        "description": "Crawler HTTP retry delay in seconds.",
        "is_secret": 0,
    },
    "crawler.auto_open_interval_seconds": {
        "value": _bootstrap_value("crawler", "auto_open_interval_seconds", 60),
        "value_type": "int",
        "description": "Scheduler auto-open polling interval.",
        "is_secret": 0,
    },
    "crawler.auto_crawl_interval_seconds": {
        "value": _bootstrap_value("crawler", "auto_crawl_interval_seconds", 600),
        "value_type": "int",
        "description": "Scheduler auto-crawl polling interval.",
        "is_secret": 0,
    },
    "crawler.auto_crawl_recent_minutes": {
        "value": _bootstrap_value("crawler", "auto_crawl_recent_minutes", 30),
        "value_type": "int",
        "description": "Recent successful crawl window in minutes.",
        "is_secret": 0,
    },
    "crawler.auto_prediction_delay_hours": {
        "value": _bootstrap_value("crawler", "auto_prediction_delay_hours", 6),
        "value_type": "int",
        "description": "Post-draw auto prediction delay in hours.",
        "is_secret": 0,
    },
    "crawler.task_poll_interval_seconds": {
        "value": _bootstrap_value("crawler", "task_poll_interval_seconds", 30),
        "value_type": "int",
        "description": "Polling interval for DB-backed scheduler tasks.",
        "is_secret": 0,
    },
    "crawler.task_lock_timeout_seconds": {
        "value": _bootstrap_value("crawler", "task_lock_timeout_seconds", 300),
        "value_type": "int",
        "description": "Stale task lock timeout in seconds.",
        "is_secret": 0,
    },
    "crawler.task_retry_delay_seconds": {
        "value": _bootstrap_value("crawler", "task_retry_delay_seconds", 60),
        "value_type": "int",
        "description": "Default retry delay for failed scheduler tasks.",
        "is_secret": 0,
    },
    "crawler.taiwan_precise_open_hour": {
        "value": _bootstrap_value("crawler", "taiwan_precise_open_hour", 22),
        "value_type": "int",
        "description": "Taiwan precise-open Beijing hour.",
        "is_secret": 0,
    },
    "crawler.taiwan_precise_open_minute": {
        "value": _bootstrap_value("crawler", "taiwan_precise_open_minute", 30),
        "value_type": "int",
        "description": "Taiwan precise-open Beijing minute.",
        "is_secret": 0,
    },
    "crawler.taiwan_retry_delays_seconds": {
        "value": _bootstrap_value("crawler", "taiwan_retry_delays_seconds", [60, 300, 900]),
        "value_type": "json",
        "description": "Taiwan precise-open retry delays.",
        "is_secret": 0,
    },
    "crawler.taiwan_max_retries": {
        "value": _bootstrap_value("crawler", "taiwan_max_retries", 3),
        "value_type": "int",
        "description": "Taiwan precise-open max retries.",
        "is_secret": 0,
    },
    "crawler.message.hk_empty_data": {
        "value": _bootstrap_value("crawler", "message_hk_empty_data", "API returned no Hong Kong draw data."),
        "value_type": "string",
        "description": "Message for empty Hong Kong crawler data.",
        "is_secret": 0,
    },
    "crawler.message.macau_empty_data": {
        "value": _bootstrap_value("crawler", "message_macau_empty_data", "API returned no Macau draw data."),
        "value_type": "string",
        "description": "Message for empty Macau crawler data.",
        "is_secret": 0,
    },
    "crawler.message.taiwan_import_only": {
        "value": _bootstrap_value("crawler", "message_taiwan_import_only", "Taiwan data must be imported from JSON."),
        "value_type": "string",
        "description": "Message for Taiwan import-only data source.",
        "is_secret": 0,
    },
    "draw.hk_default_draw_time": {
        "value": _bootstrap_value("draw", "hk_default_draw_time", "21:30"),
        "value_type": "string",
        "description": "Bootstrap Hong Kong draw time.",
        "is_secret": 0,
    },
    "draw.macau_default_draw_time": {
        "value": _bootstrap_value("draw", "macau_default_draw_time", "21:00"),
        "value_type": "string",
        "description": "Bootstrap Macau draw time.",
        "is_secret": 0,
    },
    "draw.taiwan_default_draw_time": {
        "value": _bootstrap_value("draw", "taiwan_default_draw_time", "22:30"),
        "value_type": "string",
        "description": "Bootstrap Taiwan draw time.",
        "is_secret": 0,
    },
    "draw.hk_default_collect_url": {
        "value": _bootstrap_value("draw", "hk_default_collect_url", "https://www.lnlllt.com/api.php"),
        "value_type": "string",
        "description": "Bootstrap Hong Kong collect URL.",
        "is_secret": 0,
    },
    "draw.macau_default_collect_url": {
        "value": _bootstrap_value("draw", "macau_default_collect_url", "https://www.lnlllt.com/api.php"),
        "value_type": "string",
        "description": "Bootstrap Macau collect URL.",
        "is_secret": 0,
    },
    "draw.taiwan_import_file": {
        "value": _bootstrap_value("draw", "taiwan_import_file", "data/lottery_data/lottery_page_1_20260506_194209.json"),
        "value_type": "string",
        "description": "Bootstrap Taiwan import file path.",
        "is_secret": 0,
    },
    "prediction.default_target_hit_rate": {
        "value": _bootstrap_value("prediction", "default_target_hit_rate", 0.65),
        "value_type": "float",
        "description": "Default prediction target hit rate.",
        "is_secret": 0,
    },
    "prediction.max_terms_per_year": {
        "value": _bootstrap_value("prediction", "max_terms_per_year", 365),
        "value_type": "int",
        "description": "Maximum term count per year.",
        "is_secret": 0,
    },
    "logging.max_file_size_mb": {
        "value": _bootstrap_value("logging", "max_file_size_mb", 10),
        "value_type": "int",
        "description": "Single log file size cap in MB.",
        "is_secret": 0,
    },
    "logging.backup_count": {
        "value": _bootstrap_value("logging", "backup_count", 10),
        "value_type": "int",
        "description": "Rotated log file count.",
        "is_secret": 0,
    },
    "logging.error_retention_days": {
        "value": _bootstrap_value("logging", "error_retention_days", 30),
        "value_type": "int",
        "description": "ERROR log retention in days.",
        "is_secret": 0,
    },
    "logging.warn_retention_days": {
        "value": _bootstrap_value("logging", "warn_retention_days", 7),
        "value_type": "int",
        "description": "WARNING log retention in days.",
        "is_secret": 0,
    },
    "logging.info_retention_days": {
        "value": _bootstrap_value("logging", "info_retention_days", 3),
        "value_type": "int",
        "description": "INFO/DEBUG log retention in days.",
        "is_secret": 0,
    },
    "logging.max_total_log_size_mb": {
        "value": _bootstrap_value("logging", "max_total_log_size_mb", 500),
        "value_type": "int",
        "description": "Total log directory size cap in MB.",
        "is_secret": 0,
    },
    "logging.cleanup_interval_seconds": {
        "value": _bootstrap_value("logging", "cleanup_interval_seconds", 3600),
        "value_type": "int",
        "description": "Background log cleanup interval.",
        "is_secret": 0,
    },
    "logging.slow_call_warning_ms": {
        "value": _bootstrap_value("logging", "slow_call_warning_ms", 5000),
        "value_type": "int",
        "description": "Slow-call warning threshold in milliseconds.",
        "is_secret": 0,
    },
    "legacy.images_dir": {
        "value": _bootstrap_value("legacy", "images_dir", "data/Images"),
        "value_type": "string",
        "description": "Legacy image directory.",
        "is_secret": 0,
    },
    "legacy.images_upload_bucket": {
        "value": _bootstrap_value("legacy", "images_upload_bucket", "20250322"),
        "value_type": "string",
        "description": "Legacy image upload bucket segment.",
        "is_secret": 0,
    },
    "legacy.post_list_pc": {
        "value": _bootstrap_value("legacy", "post_list_pc", 305),
        "value_type": "int",
        "description": "Legacy post-list pc identifier.",
        "is_secret": 0,
    },
    "legacy.post_list_web": {
        "value": _bootstrap_value("legacy", "post_list_web", 4),
        "value_type": "int",
        "description": "Legacy post-list web identifier.",
        "is_secret": 0,
    },
    "legacy.post_list_type": {
        "value": _bootstrap_value("legacy", "post_list_type", 3),
        "value_type": "int",
        "description": "Legacy post-list type identifier.",
        "is_secret": 0,
    },
}


def _serialize_value(value: Any, value_type: str) -> str:
    if value_type == "json":
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return ""
    return str(value)


def _deserialize_value(value_text: str, value_type: str) -> Any:
    if value_type == "int":
        return int(str(value_text).strip() or "0")
    if value_type == "float":
        return float(str(value_text).strip() or "0")
    if value_type == "bool":
        return str(value_text).strip().lower() in {"1", "true", "yes", "on"}
    if value_type == "json":
        text = str(value_text or "").strip()
        return json.loads(text) if text else None
    return str(value_text or "")


def ensure_system_config_table(conn: Any) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {CONFIG_TABLE_NAME} (
            {('id INTEGER PRIMARY KEY AUTOINCREMENT') if conn.engine == 'sqlite' else ('id BIGSERIAL PRIMARY KEY')},
            key TEXT NOT NULL UNIQUE,
            value_text TEXT NOT NULL DEFAULT '',
            value_type TEXT NOT NULL DEFAULT 'string',
            description TEXT NOT NULL DEFAULT '',
            is_secret INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )


def seed_system_config_defaults(conn: Any, *, now: str) -> None:
    ensure_system_config_table(conn)
    for key, meta in CONFIG_DEFAULTS.items():
        existing = conn.execute(
            f"SELECT id FROM {CONFIG_TABLE_NAME} WHERE key = ? LIMIT 1",
            (key,),
        ).fetchone()
        if existing:
            continue
        conn.execute(
            f"""
            INSERT INTO {CONFIG_TABLE_NAME} (
                key, value_text, value_type, description, is_secret, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                key,
                _serialize_value(meta.get("value"), str(meta.get("value_type") or "string")),
                str(meta.get("value_type") or "string"),
                str(meta.get("description") or ""),
                int(meta.get("is_secret") or 0),
                now,
                now,
            ),
        )


def get_bootstrap_config_value(key: str, fallback: Any = None) -> Any:
    meta = CONFIG_DEFAULTS.get(key)
    if meta is None:
        return fallback
    value = meta.get("value", fallback)
    return fallback if value is None else value


def get_config_from_conn(conn: Any, key: str, fallback: Any = None) -> Any:
    meta = CONFIG_DEFAULTS.get(key, {})
    default_value = meta.get("value", fallback)
    default_type = str(meta.get("value_type") or "string")

    if conn.table_exists(CONFIG_TABLE_NAME):
        row = conn.execute(
            f"SELECT value_text, value_type FROM {CONFIG_TABLE_NAME} WHERE key = ? LIMIT 1",
            (key,),
        ).fetchone()
        if row:
            row_dict = dict(row)
            return _deserialize_value(
                str(row_dict.get("value_text") or ""),
                str(row_dict.get("value_type") or default_type),
            )
    return default_value


def get_config(db_path: str | Path, key: str, fallback: Any = None) -> Any:
    with connect(db_path) as conn:
        return get_config_from_conn(conn, key, fallback)


def list_system_configs(
    db_path: str | Path,
    *,
    prefix: str = "",
    include_secrets: bool = False,
) -> list[dict[str, Any]]:
    with connect(db_path) as conn:
        ensure_system_config_table(conn)
        seed_system_config_defaults(conn, now=utc_now())
        rows = conn.execute(
            f"""
            SELECT key, value_text, value_type, description, is_secret, updated_at
            FROM {CONFIG_TABLE_NAME}
            WHERE (? = '' OR key LIKE ?)
            ORDER BY key
            """,
            (prefix, f"{prefix}%"),
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            data = dict(row)
            if data.get("is_secret") and not include_secrets:
                data["value_text"] = ""
            result.append(data)
        return result


def upsert_system_config(
    db_path: str | Path,
    *,
    key: str,
    value: Any,
    value_type: str | None = None,
    description: str | None = None,
    is_secret: bool | None = None,
) -> dict[str, Any]:
    normalized_key = str(key or "").strip()
    if not normalized_key:
        raise ValueError("Configuration key cannot be empty.")

    default_meta = CONFIG_DEFAULTS.get(normalized_key, {})
    resolved_type = str(value_type or default_meta.get("value_type") or "string")

    with connect(db_path) as conn:
        ensure_system_config_table(conn)
        timestamp = utc_now()
        existing = conn.execute(
            f"SELECT id FROM {CONFIG_TABLE_NAME} WHERE key = ? LIMIT 1",
            (normalized_key,),
        ).fetchone()
        if existing:
            conn.execute(
                f"""
                UPDATE {CONFIG_TABLE_NAME}
                SET value_text = ?, value_type = ?, description = ?, is_secret = ?, updated_at = ?
                WHERE key = ?
                """,
                (
                    _serialize_value(value, resolved_type),
                    resolved_type,
                    str(description if description is not None else default_meta.get("description") or ""),
                    int(is_secret if is_secret is not None else default_meta.get("is_secret") or 0),
                    timestamp,
                    normalized_key,
                ),
            )
        else:
            conn.execute(
                f"""
                INSERT INTO {CONFIG_TABLE_NAME} (
                    key, value_text, value_type, description, is_secret, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized_key,
                    _serialize_value(value, resolved_type),
                    resolved_type,
                    str(description if description is not None else default_meta.get("description") or ""),
                    int(is_secret if is_secret is not None else default_meta.get("is_secret") or 0),
                    timestamp,
                    timestamp,
                ),
            )
        row = conn.execute(
            f"""
            SELECT key, value_text, value_type, description, is_secret, updated_at
            FROM {CONFIG_TABLE_NAME}
            WHERE key = ?
            LIMIT 1
            """,
            (normalized_key,),
        ).fetchone()
        return dict(row) if row else {}
