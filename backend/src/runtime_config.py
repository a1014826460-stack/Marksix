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
        "description": "开奖后自动预测延迟小时数（仅作为回退值，实际由 scheduler.auto_prediction_time 控制）。",
        "is_secret": 0,
    },
    "scheduler.auto_prediction_time": {
        "value": _bootstrap_value("scheduler", "auto_prediction_time", "12:00"),
        "value_type": "time",
        "description": "每日自动预测固定触发时间（北京时间），格式 HH:mm。",
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
    # ── 彩种下一期开奖时间（由调度器从 lottery_draws.next_time 自动同步） ──
    "lottery.hk_next_time": {
        "value": "",
        "value_type": "string",
        "description": "香港彩下一期开奖时间（毫秒时间戳），由调度器自动同步，也可手动设置。",
        "is_secret": 0,
    },
    "lottery.macau_next_time": {
        "value": "",
        "value_type": "string",
        "description": "澳门彩下一期开奖时间（毫秒时间戳），由调度器自动同步，也可手动设置。",
        "is_secret": 0,
    },
    "lottery.taiwan_next_time": {
        "value": "",
        "value_type": "string",
        "description": "台湾彩下一期开奖时间（毫秒时间戳），由调度器自动同步，也可手动设置。",
        "is_secret": 0,
    },
    # ── 彩种当前期号和年份（由调度器从已开奖记录自动同步） ──
    "lottery.hk_current_period": {
        "value": "",
        "value_type": "string",
        "description": "香港彩当前期号（格式如 2026001），由调度器自动同步。",
        "is_secret": 0,
    },
    "lottery.hk_current_year": {
        "value": 0,
        "value_type": "int",
        "description": "香港彩当前年份，由调度器自动同步。",
        "is_secret": 0,
    },
    "lottery.macau_current_period": {
        "value": "",
        "value_type": "string",
        "description": "澳门彩当前期号（格式如 2026001），由调度器自动同步。",
        "is_secret": 0,
    },
    "lottery.macau_current_year": {
        "value": 0,
        "value_type": "int",
        "description": "澳门彩当前年份，由调度器自动同步。",
        "is_secret": 0,
    },
    "lottery.taiwan_current_period": {
        "value": "",
        "value_type": "string",
        "description": "台湾彩当前期号（由管理后台手工录入）。",
        "is_secret": 0,
    },
    "lottery.taiwan_current_year": {
        "value": 0,
        "value_type": "int",
        "description": "台湾彩当前年份（由管理后台手工录入）。",
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
    changed_by: str = "",
    change_reason: str = "",
) -> dict[str, Any]:
    """更新或插入 system_config 配置项，并自动记录变更历史到 system_config_history。"""
    normalized_key = str(key or "").strip()
    if not normalized_key:
        raise ValueError("Configuration key cannot be empty.")

    default_meta = CONFIG_DEFAULTS.get(normalized_key, {})
    resolved_type = str(value_type or default_meta.get("value_type") or "string")

    with connect(db_path) as conn:
        ensure_system_config_table(conn)
        timestamp = utc_now()

        # 读取旧值用于历史记录
        old_row = conn.execute(
            f"SELECT value_text FROM {CONFIG_TABLE_NAME} WHERE key = ? LIMIT 1",
            (normalized_key,),
        ).fetchone()
        old_value = str(dict(old_row).get("value_text", "")) if old_row else None

        existing = conn.execute(
            f"SELECT id FROM {CONFIG_TABLE_NAME} WHERE key = ? LIMIT 1",
            (normalized_key,),
        ).fetchone()
        new_value_text = _serialize_value(value, resolved_type)

        if existing:
            conn.execute(
                f"""
                UPDATE {CONFIG_TABLE_NAME}
                SET value_text = ?, value_type = ?, description = ?, is_secret = ?, updated_at = ?
                WHERE key = ?
                """,
                (
                    new_value_text,
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
                    new_value_text,
                    resolved_type,
                    str(description if description is not None else default_meta.get("description") or ""),
                    int(is_secret if is_secret is not None else default_meta.get("is_secret") or 0),
                    timestamp,
                    timestamp,
                ),
            )

        # 记录变更历史到 system_config_history 表
        # 仅在值确实发生变化或新建配置时记录，避免无意义的历史条目
        if old_value is not None and old_value != new_value_text:
            conn.execute(
                """
                INSERT INTO system_config_history (
                    config_key, old_value, new_value, changed_by, changed_at, change_reason, source
                ) VALUES (?, ?, ?, ?, ?, ?, 'admin')
                """,
                (normalized_key, old_value, new_value_text, changed_by or "", timestamp, change_reason or ""),
            )
        elif old_value is None:
            # 新建配置也记录历史（old_value 留空表示初始化）
            conn.execute(
                """
                INSERT INTO system_config_history (
                    config_key, old_value, new_value, changed_by, changed_at, change_reason, source
                ) VALUES (?, ?, ?, ?, ?, ?, 'admin')
                """,
                (normalized_key, "", new_value_text, changed_by or "", timestamp, change_reason or ""),
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


# ── 配置分组 ─────────────────────────────────────────

def get_config_groups() -> list[dict[str, Any]]:
    """返回配置分组列表，用于前端按分组筛选展示。"""
    return [
        {"key": "lottery", "label": "彩种配置", "prefix": "draw.", "description": "各彩种开奖时间、数据源URL、下一期开奖时间"},
        {"key": "scheduler", "label": "调度器配置", "prefix": "crawler.", "description": "自动开奖/抓取/预测延迟及固定触发时间等调度参数"},
        {"key": "prediction", "label": "预测资料配置", "prefix": "prediction.", "description": "预测生成目标命中率、最大期数"},
        {"key": "site", "label": "站点配置", "prefix": "site.", "description": "站点默认URL、Token、请求参数"},
        {"key": "logging", "label": "日志配置", "prefix": "logging.", "description": "日志保留天数、轮转大小、清理间隔"},
        {"key": "auth", "label": "认证配置", "prefix": "auth.", "description": "Session过期时间、密码迭代次数"},
        {"key": "system", "label": "系统配置", "prefix": "admin.", "description": "管理员默认账号、显示名称"},
        {"key": "legacy", "label": "旧版配置", "prefix": "legacy.", "description": "旧站图片路径、post-list参数"},
    ]


# ── 配置生效值查询 ──────────────────────────────────

def get_config_effective(db_path: str | Path, key: str) -> dict[str, Any]:
    """返回单个配置的实际生效值及其来源信息。

    优先级：数据库 system_config > config.yaml 默认值。
    如果有数据库值则使用数据库值，否则使用 config.yaml 默认值。
    """
    default_meta = CONFIG_DEFAULTS.get(key, {})
    default_value = default_meta.get("value")
    default_type = str(default_meta.get("value_type") or "string")

    db_value = None
    source = "config.yaml"
    updated_at = ""
    try:
        with connect(db_path) as conn:
            if conn.table_exists(CONFIG_TABLE_NAME):
                row = conn.execute(
                    f"SELECT value_text, value_type, updated_at FROM {CONFIG_TABLE_NAME} WHERE key = ? LIMIT 1",
                    (key,),
                ).fetchone()
                if row:
                    rd = dict(row)
                    db_value = _deserialize_value(
                        str(rd.get("value_text") or ""),
                        str(rd.get("value_type") or default_type),
                    )
                    source = "database"
                    updated_at = str(rd.get("updated_at", ""))
    except Exception:
        pass

    effective_value = db_value if db_value is not None else default_value
    return {
        "key": key,
        "value": db_value,
        "default_value": default_value,
        "effective_value": effective_value,
        "value_type": default_type,
        "source": source,
        "description": str(default_meta.get("description", "")),
        "is_secret": bool(default_meta.get("is_secret", 0)),
        "updated_at": updated_at,
    }


def list_configs_effective(
    db_path: str | Path,
    *,
    group: str = "",
    keyword: str = "",
    source: str = "",
) -> list[dict[str, Any]]:
    """返回所有配置的实际生效值列表，支持按分组、关键词、来源筛选。

    合并数据库 system_config 和 config.yaml 默认值，标注每个配置的实际来源。
    分组筛选基于 CONFIG_DEFAULTS 中 key 的前缀匹配。
    """
    # 建立 key → group 的映射
    groups = get_config_groups()
    group_map: dict[str, str] = {}
    for g in groups:
        for key in CONFIG_DEFAULTS:
            if key.startswith(g["prefix"]):
                group_map[key] = g["key"]
    # lottery.* 前缀的 key 也归入 lottery 组
    for key in CONFIG_DEFAULTS:
        if key.startswith("lottery."):
            group_map[key] = "lottery"
    # scheduler.* 前缀的 key 也归入 scheduler 组
    for key in CONFIG_DEFAULTS:
        if key.startswith("scheduler."):
            group_map[key] = "scheduler"

    # 批量读取数据库中的配置值
    db_values: dict[str, dict[str, Any]] = {}
    try:
        with connect(db_path) as conn:
            if conn.table_exists(CONFIG_TABLE_NAME):
                rows = conn.execute(
                    f"SELECT key, value_text, value_type, is_secret, description, updated_at FROM {CONFIG_TABLE_NAME} ORDER BY key"
                ).fetchall()
                for row in rows:
                    rd = dict(row)
                    db_values[str(rd["key"])] = rd
    except Exception:
        pass

    results: list[dict[str, Any]] = []
    for key, meta in CONFIG_DEFAULTS.items():
        default_value = meta.get("value")
        default_type = str(meta.get("value_type") or "string")
        is_secret = bool(meta.get("is_secret", 0))
        desc = str(meta.get("description") or "")
        config_group = group_map.get(key, "system")

        # 分组筛选
        if group and config_group != group:
            continue

        # 关键词筛选（匹配 key 或 description）
        if keyword and keyword.lower() not in key.lower() and keyword.lower() not in desc.lower():
            continue

        db_row = db_values.get(key)
        if db_row:
            db_value = _deserialize_value(
                str(db_row.get("value_text") or ""),
                str(db_row.get("value_type") or default_type),
            )
            effective_value = db_value
            config_source = "database"
            updated_at = str(db_row.get("updated_at", ""))
            if db_row.get("description"):
                desc = str(db_row["description"])
            display_value = "***已配置***" if is_secret else db_value
            raw_value = None if is_secret else db_value
        else:
            db_value = None
            effective_value = default_value
            config_source = "config.yaml"
            updated_at = ""
            display_value = "***已配置***" if (is_secret and effective_value) else effective_value
            raw_value = None if is_secret else effective_value

        # 来源筛选
        if source and config_source != source:
            continue

        # 可编辑性判断：敏感配置需要单独重新设置，不可直接编辑值
        editable = not is_secret

        # 需要重启判断：调度器和日志配置修改后通常需重启服务
        requires_restart = key.startswith(("logging.", "auth."))

        results.append({
            "key": key,
            "value": display_value,
            "raw_value": raw_value,
            "default_value": default_value,
            "effective_value": effective_value,
            "value_type": default_type,
            "group": config_group,
            "source": config_source,
            "description": desc,
            "editable": editable,
            "requires_restart": requires_restart,
            "sensitive": is_secret,
            "updated_at": updated_at,
        })

    return results


# ── 配置操作 ─────────────────────────────────────────

def reset_config(db_path: str | Path, key: str, changed_by: str = "") -> dict[str, Any]:
    """将指定配置恢复为 config.yaml 默认值，并记录变更历史。"""
    default_meta = CONFIG_DEFAULTS.get(key)
    if default_meta is None:
        raise ValueError(f"配置项 '{key}' 不存在默认值，无法恢复")

    with connect(db_path) as conn:
        ensure_system_config_table(conn)
        # 读取旧值
        old_row = conn.execute(
            f"SELECT value_text FROM {CONFIG_TABLE_NAME} WHERE key = ? LIMIT 1",
            (key,),
        ).fetchone()
        old_value = str(dict(old_row).get("value_text", "")) if old_row else ""

        default_value = default_meta.get("value")
        default_type = str(default_meta.get("value_type") or "string")
        default_desc = str(default_meta.get("description") or "")
        default_is_secret = int(default_meta.get("is_secret") or 0)
        timestamp = utc_now()
        new_value_text = _serialize_value(default_value, default_type)

        existing = conn.execute(
            f"SELECT id FROM {CONFIG_TABLE_NAME} WHERE key = ? LIMIT 1",
            (key,),
        ).fetchone()

        if existing:
            conn.execute(
                f"""
                UPDATE {CONFIG_TABLE_NAME}
                SET value_text = ?, value_type = ?, description = ?, is_secret = ?, updated_at = ?
                WHERE key = ?
                """,
                (new_value_text, default_type, default_desc, default_is_secret, timestamp, key),
            )

        # 记录变更历史
        conn.execute(
            """
            INSERT INTO system_config_history (
                config_key, old_value, new_value, changed_by, changed_at, change_reason, source
            ) VALUES (?, ?, ?, ?, ?, ?, 'admin')
            """,
            (key, old_value, new_value_text, changed_by or "", timestamp, "恢复默认值"),
        )

        row = conn.execute(
            f"SELECT key, value_text, value_type, description, is_secret, updated_at FROM {CONFIG_TABLE_NAME} WHERE key = ? LIMIT 1",
            (key,),
        ).fetchone()
        return dict(row) if row else {}


def batch_update_configs(
    db_path: str | Path,
    updates: list[dict[str, Any]],
    changed_by: str = "",
) -> dict[str, Any]:
    """批量更新配置。updates 格式: [{"key": "...", "value": ..., "value_type": "..."}, ...]

    逐项执行 upsert，返回成功/失败统计。
    """
    success = 0
    failed: list[dict[str, str]] = []
    for item in updates:
        key = str(item.get("key", ""))
        value = item.get("value")
        value_type = str(item.get("value_type", "") or "")
        try:
            upsert_system_config(
                db_path,
                key=key,
                value=value,
                value_type=value_type if value_type else None,
                changed_by=changed_by,
            )
            success += 1
        except Exception as e:
            failed.append({"key": key, "error": str(e)})
    return {"success": success, "failed": len(failed), "failed_items": failed}


# ── 配置变更历史 ────────────────────────────────────

def get_config_history(
    db_path: str | Path,
    *,
    key: str = "",
    page: int = 1,
    page_size: int = 30,
) -> dict[str, Any]:
    """查询 system_config_history 变更记录，支持按 config_key 筛选。"""
    filters: list[str] = []
    params: list[Any] = []
    if key:
        filters.append("config_key = ?")
        params.append(key)

    with connect(db_path) as conn:
        where = (" WHERE " + " AND ".join(filters)) if filters else ""
        offset = max(0, page - 1) * page_size
        total = int(
            conn.execute(
                f"SELECT COUNT(*) AS cnt FROM system_config_history{where}", params
            ).fetchone()["cnt"] or 0
        )
        rows = conn.execute(
            f"SELECT * FROM system_config_history{where} ORDER BY changed_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()

    return {
        "items": [dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


# ── 配置值校验 ──────────────────────────────────────

def validate_config_value(key: str, value: Any, value_type: str) -> tuple[bool, str]:
    """校验配置值的类型和业务约束。返回 (is_valid, error_message)。

    支持的 value_type: int, float, bool, string, json, time
    部分 int 类型配置有正整数的业务约束。
    """
    if value_type == "int":
        try:
            v = int(value)
            # 需要正整数的配置项
            positive_int_keys = {
                "crawler.auto_open_interval_seconds",
                "crawler.auto_crawl_interval_seconds",
                "crawler.auto_crawl_recent_minutes",
                "crawler.auto_prediction_delay_hours",
                "crawler.task_poll_interval_seconds",
                "crawler.task_lock_timeout_seconds",
                "crawler.task_retry_delay_seconds",
                "crawler.taiwan_precise_open_hour",
                "crawler.taiwan_precise_open_minute",
                "crawler.taiwan_max_retries",
                "crawler.http_timeout_seconds",
                "crawler.http_retry_count",
                "crawler.interval_seconds",
                "prediction.max_terms_per_year",
                "logging.max_file_size_mb",
                "logging.backup_count",
                "logging.error_retention_days",
                "logging.warn_retention_days",
                "logging.info_retention_days",
                "logging.max_total_log_size_mb",
                "logging.cleanup_interval_seconds",
                "logging.slow_call_warning_ms",
                "auth.session_ttl_seconds",
                "auth.password_iterations",
                "site.start_web_id",
                "site.end_web_id",
                "site.request_limit",
            }
            if key in positive_int_keys and v < 0:
                return False, f"'{key}' 不能为负数，当前值: {v}"
            return True, ""
        except (ValueError, TypeError):
            return False, f"'{key}' 需要整数类型，当前值: {value}"

    if value_type == "float":
        try:
            float(value)
            return True, ""
        except (ValueError, TypeError):
            return False, f"'{key}' 需要浮点数类型，当前值: {value}"

    if value_type == "bool":
        if isinstance(value, bool):
            return True, ""
        if str(value).strip().lower() in {"true", "false", "1", "0", "yes", "no", "on", "off"}:
            return True, ""
        return False, f"'{key}' 需要布尔类型 (true/false)，当前值: {value}"

    if value_type == "json":
        if isinstance(value, (dict, list)):
            return True, ""
        try:
            json.loads(str(value))
            return True, ""
        except (json.JSONDecodeError, TypeError):
            return False, f"'{key}' 需要合法 JSON 格式，当前值: {value}"

    if value_type == "time":
        import re as _re
        if _re.match(r"^\d{1,2}:\d{2}(:\d{2})?$", str(value).strip()):
            return True, ""
        return False, f"'{key}' 需要 HH:mm 或 HH:mm:ss 时间格式，当前值: {value}"

    # string 类型不做校验
    return True, ""


# ── 彩种 next_time 映射 ──────────────────────────────

# lottery_type_id → system_config key 的映射，
# 供调度器在爬虫更新 lottery_draws.next_time 后同步写入 system_config。
LOTTERY_NEXT_TIME_CONFIG_KEYS: dict[int, str] = {
    1: "lottery.hk_next_time",
    2: "lottery.macau_next_time",
    3: "lottery.taiwan_next_time",
}


def sync_lottery_next_time_to_system_config(
    db_path: str | Path,
    lottery_type_id: int,
    next_time: str,
) -> None:
    """将彩种下一期开奖时间同步写入 system_config 表。

    由调度器在爬虫更新 lottery_draws.next_time 后调用，
    确保 system_config 中存储的值为最新。
    """
    config_key = LOTTERY_NEXT_TIME_CONFIG_KEYS.get(lottery_type_id)
    if not config_key:
        return
    try:
        upsert_system_config(
            db_path,
            key=config_key,
            value=next_time,
            value_type="string",
            changed_by="scheduler",
            change_reason="从 lottery_draws.next_time 自动同步",
        )
    except Exception:
        pass


def get_lottery_next_time_from_config(
    db_path: str | Path,
    lottery_type_id: int,
) -> str:
    """从 system_config 读取彩种下一期开奖时间。"""
    config_key = LOTTERY_NEXT_TIME_CONFIG_KEYS.get(lottery_type_id)
    if not config_key:
        return ""
    try:
        return str(get_config(db_path, config_key, ""))
    except Exception:
        return ""
