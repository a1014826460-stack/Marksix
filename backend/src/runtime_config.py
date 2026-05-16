"""运行时配置中心——数据库优先，作为单一可信配置源。

所有配置均存储在 system_config 数据库表中。下方 CONFIG_DEFAULTS 字典用于在
配置表尚未初始化时提供启动默认值或回退值。服务运行后，管理后台界面或 API
是读取和更新配置的标准入口。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from db import connect, utc_now

CONFIG_TABLE_NAME = "system_config"

CONFIG_DEFAULTS: dict[str, dict[str, Any]] = {
    "database.default_postgres_dsn": {
        "value": "",
        "value_type": "string",
        "description": "初始启动用 PostgreSQL DSN。",
        "is_secret": 1,
    },
    "admin.username": {
        "value": "admin",
        "value_type": "string",
        "description": "初始管理员用户名。",
        "is_secret": 0,
    },
    "admin.password": {
        "value": "admin123",
        "value_type": "string",
        "description": "初始管理员密码。",
        "is_secret": 1,
    },
    "admin.display_name": {
        "value": "系统管理员",
        "value_type": "string",
        "description": "初始管理员显示名称。",
        "is_secret": 0,
    },
    "admin_email": {
        "value": "1014826460@qq.com",
        "value_type": "string",
        "description": "管理员告警邮箱，台湾彩缺期等关键告警优先发送到该地址。",
        "is_secret": 0,
    },
    "admin.role": {
        "value": "super_admin",
        "value_type": "string",
        "description": "初始管理员角色。",
        "is_secret": 0,
    },
    "auth.session_ttl_seconds": {
        "value": 86400,
        "value_type": "int",
        "description": "管理员会话过期秒数。",
        "is_secret": 0,
    },
    "auth.password_iterations": {
        "value": 260000,
        "value_type": "int",
        "description": "PBKDF2 密码哈希迭代次数。",
        "is_secret": 0,
    },
    "crawler.interval_seconds": {
        "value": 3600,
        "value_type": "int",
        "description": "旧版爬虫间隔。",
        "is_secret": 0,
    },
    "crawler.http_timeout_seconds": {
        "value": 30,
        "value_type": "int",
        "description": "爬虫 HTTP 超时秒数。",
        "is_secret": 0,
    },
    "crawler.http_retry_count": {
        "value": 2,
        "value_type": "int",
        "description": "爬虫 HTTP 重试次数。",
        "is_secret": 0,
    },
    "crawler.http_retry_delay_seconds": {
        "value": 1.0,
        "value_type": "float",
        "description": "爬虫 HTTP 重试延迟秒数。",
        "is_secret": 0,
    },
    "crawler.auto_open_interval_seconds": {
        "value": 60,
        "value_type": "int",
        "description": "调度器自动开奖轮询间隔。",
        "is_secret": 0,
    },
    "crawler.auto_crawl_interval_seconds": {
        "value": 600,
        "value_type": "int",
        "description": "调度器自动抓取轮询间隔。",
        "is_secret": 0,
    },
    "crawler.auto_crawl_recent_minutes": {
        "value": 30,
        "value_type": "int",
        "description": "最近成功抓取判定窗口分钟数。",
        "is_secret": 0,
    },
    "crawler.auto_prediction_delay_hours": {
        "value": 6,
        "value_type": "int",
        "description": "开奖后自动预测延迟小时数（已废弃，由 daily_prediction_cron_time 替代，当前功能已暂停）。",
        "is_secret": 0,
    },
    "scheduler.auto_prediction_time": {
        "value": "12:00",
        "value_type": "time",
        "description": "每日自动预测固定触发时间（北京时间），格式 HH:mm（已废弃，由 daily_prediction_cron_time 替代）。",
        "is_secret": 0,
    },
    "daily_prediction_cron_time": {
        "value": "12:00",
        "value_type": "time",
        "description": "每日自动预测触发时间（北京时间），格式 HH:mm。管理员可在后台修改。",
        "is_secret": 0,
    },
    "history_backfill_delay_after_draw": {
        "value": 5,
        "value_type": "int",
        "description": "开奖后延迟执行历史回填任务的分钟数。默认 5 分钟。",
        "is_secret": 0,
    },
    "crawler.task_poll_interval_seconds": {
        "value": 30,
        "value_type": "int",
        "description": "数据库调度任务轮询间隔。",
        "is_secret": 0,
    },
    "crawler.task_lock_timeout_seconds": {
        "value": 300,
        "value_type": "int",
        "description": "过期任务锁超时秒数。",
        "is_secret": 0,
    },
    "crawler.task_retry_delay_seconds": {
        "value": 60,
        "value_type": "int",
        "description": "失败调度任务默认重试延迟。",
        "is_secret": 0,
    },
    "crawler.taiwan_precise_open_hour": {
        "value": 22,
        "value_type": "int",
        "description": "【已废弃】请使用 draw.taiwan_default_draw_time。台湾彩精准开奖北京时间小时。",
        "is_secret": 0,
    },
    "crawler.taiwan_precise_open_minute": {
        "value": 30,
        "value_type": "int",
        "description": "【已废弃】请使用 draw.taiwan_default_draw_time。台湾彩精准开奖北京时间分钟。",
        "is_secret": 0,
    },
    "crawler.taiwan_retry_delays_seconds": {
        "value": [60, 300, 900],
        "value_type": "json",
        "description": "台湾彩精准开奖重试延迟列表。",
        "is_secret": 0,
    },
    "crawler.taiwan_max_retries": {
        "value": 3,
        "value_type": "int",
        "description": "台湾彩精准开奖最大重试次数。",
        "is_secret": 0,
    },
    "crawler.crawl_interval_near_draw": {
        "value": 10,
        "value_type": "int",
        "description": "开奖时间窗口内（±5分钟）的抓取轮询间隔秒数。",
        "is_secret": 0,
    },
    "crawler.crawl_interval_far_draw": {
        "value": 300,
        "value_type": "int",
        "description": "开奖时间窗口外的抓取轮询间隔秒数。",
        "is_secret": 0,
    },
    "crawler.crawl_interval_chase": {
        "value": 5,
        "value_type": "int",
        "description": "开奖超时未获数据时的应急加速轮询间隔秒数。",
        "is_secret": 0,
    },
    "crawler.backup_fail_count_threshold": {
        "value": 2,
        "value_type": "int",
        "description": "主采集 URL 连续失败次数达到此值后切换备用 URL。",
        "is_secret": 0,
    },
    "crawler.message.hk_empty_data": {
        "value": "API returned no Hong Kong draw data.",
        "value_type": "string",
        "description": "香港彩抓取数据为空提示。",
        "is_secret": 0,
    },
    "crawler.message.macau_empty_data": {
        "value": "API returned no Macau draw data.",
        "value_type": "string",
        "description": "澳门彩抓取数据为空提示。",
        "is_secret": 0,
    },
    "crawler.message.taiwan_import_only": {
        "value": "Taiwan data must be imported from JSON.",
        "value_type": "string",
        "description": "台湾彩仅支持导入的数据源提示。",
        "is_secret": 0,
    },
    "draw.hk_default_draw_time": {
        "value": "21:30",
        "value_type": "string",
        "description": "初始香港彩开奖时间。",
        "is_secret": 0,
    },
    "draw.macau_default_draw_time": {
        "value": "21:30",
        "value_type": "string",
        "description": "初始澳门彩开奖时间。",
        "is_secret": 0,
    },
    "draw.taiwan_default_draw_time": {
        "value": "22:30",
        "value_type": "string",
        "description": "台湾彩开奖时间（北京时间 HH:MM）。用于精准开奖调度和下一期时间计算。",
        "is_secret": 0,
    },
    "draw.hk_default_collect_url": {
        "value": "https://www.lnlllt.com/api.php",
        "value_type": "string",
        "description": "初始香港彩采集 URL。",
        "is_secret": 0,
    },
    "draw.macau_default_collect_url": {
        "value": "https://www.lnlllt.com/api.php",
        "value_type": "string",
        "description": "初始澳门彩采集 URL。",
        "is_secret": 0,
    },
    "draw.hk_backup_collect_url": {
        "value": "",
        "value_type": "string",
        "description": "香港彩备用采集 URL，主 URL 连续失败后自动切换。",
        "is_secret": 0,
    },
    "draw.macau_backup_collect_url": {
        "value": "",
        "value_type": "string",
        "description": "澳门彩备用采集 URL，主 URL 连续失败后自动切换。",
        "is_secret": 0,
    },
    "draw.taiwan_import_file": {
        "value": "data/lottery_data/lottery_page_1_20260506_194209.json",
        "value_type": "string",
        "description": "初始台湾彩导入文件路径。",
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
        "value": 0.65,
        "value_type": "float",
        "description": "默认预测目标命中率。",
        "is_secret": 0,
    },
    "prediction.max_terms_per_year": {
        "value": 365,
        "value_type": "int",
        "description": "每年最大期数。",
        "is_secret": 0,
    },
    "prediction.recent_period_count": {
        "value": 10,
        "value_type": "int",
        "description": "回补检查时向前追溯的期数。自动预测和回填API均据此决定检查范围。",
        "is_secret": 0,
    },
    "logging.max_file_size_mb": {
        "value": 10,
        "value_type": "int",
        "description": "单个日志文件大小上限 MB。",
        "is_secret": 0,
    },
    "logging.backup_count": {
        "value": 10,
        "value_type": "int",
        "description": "轮转日志文件保留数量。",
        "is_secret": 0,
    },
    "logging.error_retention_days": {
        "value": 30,
        "value_type": "int",
        "description": "ERROR 日志保留天数。",
        "is_secret": 0,
    },
    "logging.warn_retention_days": {
        "value": 7,
        "value_type": "int",
        "description": "WARNING 日志保留天数。",
        "is_secret": 0,
    },
    "logging.info_retention_days": {
        "value": 3,
        "value_type": "int",
        "description": "INFO/DEBUG 日志保留天数。",
        "is_secret": 0,
    },
    "logging.max_total_log_size_mb": {
        "value": 500,
        "value_type": "int",
        "description": "日志目录总大小上限 MB。",
        "is_secret": 0,
    },
    "logging.cleanup_interval_seconds": {
        "value": 3600,
        "value_type": "int",
        "description": "后台日志清理间隔。",
        "is_secret": 0,
    },
    "logging.slow_call_warning_ms": {
        "value": 5000,
        "value_type": "int",
        "description": "慢调用告警阈值毫秒数。",
        "is_secret": 0,
    },
    # ── 邮件报警基础配置 ──
    "database.backup_enabled": {
        "value": True,
        "value_type": "bool",
        "description": "Enable scheduled PostgreSQL logical backups.",
        "is_secret": 0,
    },
    "database.backup_times": {
        "value": ["00:00", "11:00"],
        "value_type": "json",
        "description": "Daily PostgreSQL backup times in Beijing time, HH:MM list.",
        "is_secret": 0,
    },
    "database.backup_dir": {
        "value": "data/backups",
        "value_type": "string",
        "description": "Directory for pg_dump -Fc backup files. Relative paths are under backend/.",
        "is_secret": 0,
    },
    "database.backup_retention_days": {
        "value": 30,
        "value_type": "int",
        "description": "Retention days for scheduled PostgreSQL .dump backup files.",
        "is_secret": 0,
    },
    "database.pg_dump_path": {
        "value": "pg_dump",
        "value_type": "string",
        "description": "pg_dump executable path. Set an absolute path if it is not on PATH.",
        "is_secret": 0,
    },
    "alert.email_enabled": {
        "value": True,
        "value_type": "bool",
        "description": "是否启用邮件报警。关闭后所有报警只记日志不发邮件。",
        "is_secret": 0,
    },
    "alert.email_recipients": {
        "value": ["1014826460@qq.com"],
        "value_type": "json",
        "description": "报警邮件收件人列表。",
        "is_secret": 0,
    },
    "alert.smtp_host": {
        "value": "smtp.qq.com",
        "value_type": "string",
        "description": "SMTP 服务器地址。",
        "is_secret": 0,
    },
    "alert.smtp_port": {
        "value": 587,
        "value_type": "int",
        "description": "SMTP 服务器端口（587=TLS, 465=SSL）。",
        "is_secret": 0,
    },
    "alert.smtp_username": {
        "value": "",
        "value_type": "string",
        "description": "SMTP 登录用户名（通常为邮箱地址）。",
        "is_secret": 0,
    },
    "alert.smtp_password": {
        "value": "",
        "value_type": "string",
        "description": "SMTP 登录密码或授权码。",
        "is_secret": 0,
    },
    "alert.smtp_from_name": {
        "value": "Liuhecai 报警系统",
        "value_type": "string",
        "description": "报警邮件发件人显示名称。",
        "is_secret": 0,
    },
    "alert.crawler_retry_threshold": {
        "value": 3,
        "value_type": "int",
        "description": "爬虫连续失败次数达到此阈值后触发报警。",
        "is_secret": 0,
    },
    "alert.draw_yellow_timeout_seconds": {
        "value": 30,
        "value_type": "int",
        "description": "开奖后 N 秒数据未入库触发黄色预警（日志 + 加速轮询）。",
        "is_secret": 0,
    },
    "alert.draw_orange_timeout_seconds": {
        "value": 120,
        "value_type": "int",
        "description": "开奖后 N 秒数据未入库触发橙色告警（邮件 + 备用 URL 切换）。",
        "is_secret": 0,
    },
    "alert.draw_red_timeout_seconds": {
        "value": 300,
        "value_type": "int",
        "description": "开奖后 N 秒数据未入库触发红色告警（邮件 + 需人工介入）。",
        "is_secret": 0,
    },
    "legacy.images_dir": {
        "value": "data/Images",
        "value_type": "string",
        "description": "旧版图片目录。",
        "is_secret": 0,
    },
    "legacy.images_upload_bucket": {
        "value": "20250322",
        "value_type": "string",
        "description": "旧版图片上传桶分段。",
        "is_secret": 0,
    },
    "legacy.post_list_pc": {
        "value": 305,
        "value_type": "int",
        "description": "旧版 post-list pc 标识。",
        "is_secret": 0,
    },
    "legacy.post_list_web": {
        "value": 4,
        "value_type": "int",
        "description": "旧版 post-list web 标识。",
        "is_secret": 0,
    },
    "legacy.post_list_type": {
        "value": 3,
        "value_type": "int",
        "description": "旧版 post-list type 标识。",
        "is_secret": 0,
    },
}

def _serialize_value(value: Any, value_type: str) -> str:
    """将配置值序列化为数据库可存储的字符串。

    根据配置项声明的 value_type 对原始 Python 值进行转换。JSON 类型会使用
    ``json.dumps`` 保留中文字符，其余类型统一转换为字符串；空值会写入空字符串，
    以适配 system_config.value_text 字段的非空约束。

    Args:
        value (Any): 待序列化的原始配置值，可以是字符串、数字、布尔值、列表、字典
            或 ``None``。
        value_type (str): 配置值类型标识，例如 ``string``、``int``、``float``、
            ``bool``、``json`` 或 ``time``。

    Returns:
        str: 可写入数据库 ``value_text`` 字段的字符串表示。

    Raises:
        TypeError: 当 ``value_type`` 为 ``json`` 且 ``value`` 无法被 JSON 序列化时抛出。
    """
    if value_type == "json":
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return ""
    return str(value)

def _deserialize_value(value_text: str, value_type: str) -> Any:
    """将数据库中的配置字符串反序列化为对应的 Python 值。

    按 ``value_type`` 将 ``system_config.value_text`` 中的字符串恢复为整数、浮点数、
    布尔值、JSON 对象或普通字符串。空整数与空浮点数会分别按 ``0`` 和 ``0.0`` 处理，
    空 JSON 字符串会返回 ``None``。

    Args:
        value_text (str): 数据库中读取到的配置文本值。
        value_type (str): 配置值类型标识，例如 ``string``、``int``、``float``、
            ``bool``、``json`` 或 ``time``。

    Returns:
        Any: 反序列化后的配置值，具体类型由 ``value_type`` 决定。

    Raises:
        ValueError: 当整数、浮点数或 JSON 文本格式非法时抛出。
        json.JSONDecodeError: 当 ``value_type`` 为 ``json`` 且文本不是合法 JSON 时抛出。
    """
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
    """确保系统配置表存在。

    根据当前连接的数据库引擎创建 ``system_config`` 表。SQLite 使用
    ``AUTOINCREMENT`` 主键，PostgreSQL 使用 ``BIGSERIAL`` 主键，其他字段保持一致。
    如果表已存在，则不会修改已有表结构。

    Args:
        conn (Any): 数据库连接对象，需提供 ``engine`` 属性和 ``execute`` 方法。

    Returns:
        None: 该函数仅执行建表语句，不返回业务数据。

    Raises:
        Exception: 当数据库连接不可用、SQL 执行失败或权限不足时由底层数据库驱动抛出。
    """
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
    """将默认配置种子数据写入系统配置表。

    遍历 ``CONFIG_DEFAULTS`` 中的所有配置项，仅在数据库中不存在对应 key 时插入默认值。
    已存在的配置不会被覆盖，避免覆盖管理员在后台或 API 中做出的修改。

    Args:
        conn (Any): 数据库连接对象，需支持 ``execute``、``fetchone`` 等数据库操作。
        now (str): 当前时间字符串，用于填充 ``created_at`` 和 ``updated_at`` 字段。

    Returns:
        None: 该函数仅负责初始化缺失配置，不返回业务数据。

    Raises:
        TypeError: 当默认配置中的 JSON 值无法序列化时抛出。
        Exception: 当建表、查询或插入配置失败时由底层数据库驱动抛出。
    """
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
    """读取启动阶段使用的默认配置值。

    仅从 ``CONFIG_DEFAULTS`` 中读取配置，不访问数据库。该函数适合在数据库连接尚未
    建立或系统初始化早期使用，用于获取启动所需的回退配置。

    Args:
        key (str): 配置项 key。
        fallback (Any, optional): 当 key 不存在或默认值为 ``None`` 时返回的回退值。
            默认为 ``None``。

    Returns:
        Any: 配置项默认值；如果配置不存在或默认值为空，则返回 ``fallback``。
    """
    meta = CONFIG_DEFAULTS.get(key)
    if meta is None:
        return fallback
    value = meta.get("value", fallback)
    return fallback if value is None else value

def get_config_from_conn(conn: Any, key: str, fallback: Any = None) -> Any:
    """基于已有数据库连接读取单个配置值。

    优先从 ``system_config`` 表读取指定 key 的配置并按其 ``value_type`` 转换类型；
    如果配置表不存在或没有对应记录，则返回 ``CONFIG_DEFAULTS`` 中的默认值或传入的
    ``fallback``。该函数不会主动创建或初始化配置表。

    Args:
        conn (Any): 已打开的数据库连接对象，需提供 ``table_exists`` 和 ``execute`` 方法。
        key (str): 需要读取的配置项 key。
        fallback (Any, optional): 当默认配置和数据库配置均不存在时返回的回退值。
            默认为 ``None``。

    Returns:
        Any: 实际读取到的配置值，类型由数据库中的 ``value_type`` 或默认配置类型决定。

    Raises:
        ValueError: 当数据库中的配置值无法按目标类型转换时抛出。
        Exception: 当数据库查询失败时由底层数据库驱动抛出。
    """
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
    """打开数据库连接并读取单个配置值。

    这是 ``get_config_from_conn`` 的便捷封装，用于调用方只持有数据库路径时读取配置。
    函数会自动建立连接并在读取结束后关闭连接。

    Args:
        db_path (str | Path): 数据库路径或数据库连接配置路径，具体格式由 ``connect`` 实现决定。
        key (str): 需要读取的配置项 key。
        fallback (Any, optional): 当数据库和默认配置中均没有该 key 时返回的回退值。
            默认为 ``None``。

    Returns:
        Any: 实际生效的配置值。

    Raises:
        ValueError: 当配置值无法按声明类型反序列化时抛出。
        Exception: 当数据库连接或查询失败时由底层实现抛出。
    """
    with connect(db_path) as conn:
        return get_config_from_conn(conn, key, fallback)

def list_system_configs(
    db_path: str | Path,
    *,
    prefix: str = "",
    include_secrets: bool = False,
) -> list[dict[str, Any]]:
    """列出系统配置表中的配置记录。

    函数会确保 ``system_config`` 表存在，并将 ``CONFIG_DEFAULTS`` 中缺失的默认配置
    写入数据库。支持按 key 前缀筛选；对于敏感配置，默认会隐藏 ``value_text``，避免
    将密钥、密码等内容直接返回给前端。

    Args:
        db_path (str | Path): 数据库路径或连接配置路径。
        prefix (str, optional): 配置 key 前缀筛选条件。空字符串表示不筛选。
            默认为空字符串。
        include_secrets (bool, optional): 是否返回敏感配置的真实值。为 ``False`` 时，
            敏感配置的 ``value_text`` 会被置为空字符串。默认为 ``False``。

    Returns:
        list[dict[str, Any]]: 配置记录列表，每项包含 ``key``、``value_text``、
        ``value_type``、``description``、``is_secret`` 和 ``updated_at``。

    Raises:
        Exception: 当数据库连接、建表、初始化或查询失败时由底层实现抛出。
    """
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
    """更新或插入系统配置项，并记录配置变更历史。

    该函数会对传入的配置 key 进行标准化处理。如果配置已存在，则更新其值、类型、
    描述、敏感标记和更新时间；如果不存在，则插入新配置。配置值会根据 ``value_type``
    序列化后存入 ``value_text``。当值发生变化或新建配置时，会向
    ``system_config_history`` 写入一条变更记录，便于后台审计。

    Args:
        db_path (str | Path): 数据库路径或连接配置路径。
        key (str): 配置项 key，不能为空。
        value (Any): 需要写入的配置值。
        value_type (str | None, optional): 配置值类型。为空时优先使用默认配置中的
            ``value_type``，仍不存在时使用 ``string``。默认为 ``None``。
        description (str | None, optional): 配置说明。为空时使用默认配置中的说明。
            默认为 ``None``。
        is_secret (bool | None, optional): 是否为敏感配置。为空时使用默认配置中的
            ``is_secret``。默认为 ``None``。
        changed_by (str, optional): 变更操作人标识，用于写入历史记录。默认为空字符串。
        change_reason (str, optional): 变更原因说明，用于写入历史记录。默认为空字符串。

    Returns:
        dict[str, Any]: 更新或插入后的配置记录；如果写入后未查询到记录，则返回空字典。

    Raises:
        ValueError: 当 ``key`` 为空时抛出。
        TypeError: 当配置值无法按指定类型序列化时抛出。
        Exception: 当数据库连接、写入或历史记录插入失败时由底层实现抛出。
    """
    normalized_key = str(key or "").strip()
    if not normalized_key:
        raise ValueError("配置项 key 不能为空。")

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
    """返回前端展示使用的配置分组定义。

    配置分组用于管理后台按业务域筛选和展示配置项。每个分组包含分组 key、
    展示名称、匹配前缀和简要说明。

    Returns:
        list[dict[str, Any]]: 配置分组列表，每项包含 ``key``、``label``、``prefix``
        和 ``description``。
    """
    return [
        {"key": "lottery", "label": "彩种配置", "prefix": "draw.", "description": "各彩种开奖时间、数据源 URL、下一期开奖时间"},
        {"key": "scheduler", "label": "调度器配置", "prefix": "crawler.", "description": "自动开奖/抓取/预测延迟及固定触发时间等调度参数"},
        {"key": "prediction", "label": "预测资料配置", "prefix": "prediction.", "description": "预测生成目标命中率、最大期数"},
        {"key": "alert", "label": "报警配置", "prefix": "alert.", "description": "邮件报警开关、SMTP 服务参数、报警阈值"},
        {"key": "site", "label": "站点配置", "prefix": "site.", "description": "站点默认 URL、令牌、请求参数"},
        {"key": "logging", "label": "日志配置", "prefix": "logging.", "description": "日志保留天数、轮转大小、清理间隔"},
        {"key": "auth", "label": "认证配置", "prefix": "auth.", "description": "会话过期时间、密码迭代次数"},
        {"key": "system", "label": "系统配置", "prefix": "admin.", "description": "管理员默认账号、显示名称"},
        {"key": "legacy", "label": "旧版配置", "prefix": "legacy.", "description": "旧站图片路径、旧版列表参数"},
    ]

# ── 配置生效值查询 ──────────────────────────────────

def get_config_effective(db_path: str | Path, key: str) -> dict[str, Any]:
    """查询单个配置项的实际生效值及来源。

    函数会优先读取数据库 ``system_config`` 表中的配置值；如果数据库不存在、配置项不存在
    或读取失败，则回退到 ``CONFIG_DEFAULTS`` 中的默认值，并标注配置来源。该接口适合
    管理后台展示“当前值、默认值、实际生效值、来源”等诊断信息。

    Args:
        db_path (str | Path): 数据库路径或连接配置路径。
        key (str): 需要查询的配置项 key。

    Returns:
        dict[str, Any]: 配置生效信息，包含 ``key``、``value``、``default_value``、
        ``effective_value``、``value_type``、``source``、``description``、``is_secret``
        和 ``updated_at``。
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
    """查询所有配置项的实际生效值列表。

    函数会合并 ``CONFIG_DEFAULTS`` 与数据库 ``system_config`` 中的配置值，为每个配置项
    标注实际来源、分组、是否可编辑、是否敏感以及是否通常需要重启服务。支持按分组、
    关键词和来源筛选，适合后台配置管理页使用。

    Args:
        db_path (str | Path): 数据库路径或连接配置路径。
        group (str, optional): 配置分组 key。为空字符串时不按分组筛选。默认为空字符串。
        keyword (str, optional): 关键词筛选条件，会匹配配置 key 和描述。默认为空字符串。
        source (str, optional): 配置来源筛选条件，例如 ``database`` 或 ``config.yaml``。
            为空字符串时不按来源筛选。默认为空字符串。

    Returns:
        list[dict[str, Any]]: 配置生效信息列表，每项包含展示值、原始值、默认值、
        实际生效值、分组、来源、描述、敏感标记、可编辑标记、重启提示和更新时间。
    """
    # 建立配置键到分组标识的映射
    groups = get_config_groups()
    group_map: dict[str, str] = {}
    for g in groups:
        for key in CONFIG_DEFAULTS:
            if key.startswith(g["prefix"]):
                group_map[key] = g["key"]
    # 以 lottery.* 开头的配置项也归入 lottery 组
    for key in CONFIG_DEFAULTS:
        if key.startswith("lottery."):
            group_map[key] = "lottery"
    # 以 scheduler.* 开头的配置项也归入 scheduler 组
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

        # 关键词筛选（匹配配置键或说明）
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
    """将指定配置项恢复为默认值，并记录变更历史。

    根据 ``CONFIG_DEFAULTS`` 中的定义读取默认值、类型、描述和敏感标记，将对应数据库
    配置恢复为默认状态，同时向 ``system_config_history`` 写入“恢复默认值”的审计记录。

    Args:
        db_path (str | Path): 数据库路径或连接配置路径。
        key (str): 需要恢复默认值的配置项 key。
        changed_by (str, optional): 执行恢复操作的用户或系统标识。默认为空字符串。

    Returns:
        dict[str, Any]: 恢复后的配置记录；如果恢复后未查询到记录，则返回空字典。

    Raises:
        ValueError: 当配置项不存在于 ``CONFIG_DEFAULTS`` 中，无法确定默认值时抛出。
        TypeError: 当默认值无法按默认类型序列化时抛出。
        Exception: 当数据库连接、更新或历史记录写入失败时由底层实现抛出。
    """
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
    """批量更新多个系统配置项。

    逐项调用 ``upsert_system_config`` 执行配置写入，并统计成功数量和失败条目。单个配置
    更新失败不会中断后续配置处理，失败信息会记录在返回结果的 ``failed_items`` 中。

    Args:
        db_path (str | Path): 数据库路径或连接配置路径。
        updates (list[dict[str, Any]]): 待更新配置列表。每项通常包含 ``key``、``value``
            和可选的 ``value_type``。
        changed_by (str, optional): 批量变更操作人标识，用于写入历史记录。默认为空字符串。

    Returns:
        dict[str, Any]: 批量更新结果，包含 ``success`` 成功数量、``failed`` 失败数量
        和 ``failed_items`` 失败明细列表。
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
    """分页查询系统配置变更历史。

    从 ``system_config_history`` 表读取配置变更记录，支持按配置 key 筛选，并返回分页
    元数据，供后台配置审计页面展示。

    Args:
        db_path (str | Path): 数据库路径或连接配置路径。
        key (str, optional): 配置项 key 筛选条件。为空字符串时查询全部配置历史。
            默认为空字符串。
        page (int, optional): 页码，从 1 开始。小于 1 时会按第一页处理偏移量。默认为 1。
        page_size (int, optional): 每页记录数。默认为 30。

    Returns:
        dict[str, Any]: 分页结果，包含 ``items``、``total``、``page``、``page_size``
        和 ``total_pages``。

    Raises:
        Exception: 当历史表不存在、数据库连接失败或查询失败时由底层实现抛出。
    """
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
    """校验配置值类型及基础业务约束。

    根据传入的 ``value_type`` 对配置值进行类型校验，支持 ``int``、``float``、``bool``、
    ``string``、``json`` 和 ``time``。部分整数配置项会额外校验不能为负数。函数不会抛出
    校验异常，而是通过布尔值和错误消息返回校验结果。

    Args:
        key (str): 配置项 key，用于定位配置并生成错误提示。
        value (Any): 待校验的配置值。
        value_type (str): 配置值类型标识。

    Returns:
        tuple[bool, str]: 二元组 ``(is_valid, error_message)``。``is_valid`` 表示是否
        校验通过；``error_message`` 在校验失败时包含具体原因，校验成功时为空字符串。
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
                "draw.taiwan_default_draw_time",
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

    # 字符串类型不做校验
    return True, ""

# ── 彩种下一期开奖时间映射 ────────────────────────────

# 彩种 ID 到 system_config 配置键的映射，
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
    """同步彩种下一期开奖时间到系统配置表。

    根据 ``lottery_type_id`` 查找对应的 ``lottery.*_next_time`` 配置 key，并将爬虫或调度器
    计算出的下一期开奖时间写入 ``system_config``。写入失败会被静默忽略，避免调度器主流程
    因配置同步失败而中断。

    Args:
        db_path (str | Path): 数据库路径或连接配置路径。
        lottery_type_id (int): 彩种 ID，当前约定 1 为香港彩、2 为澳门彩、3 为台湾彩。
        next_time (str): 下一期开奖时间，通常为毫秒时间戳字符串或外部源提供的时间字符串。

    Returns:
        None: 该函数只执行同步写入，不返回业务数据。
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
    """从系统配置表读取指定彩种的下一期开奖时间。

    根据 ``lottery_type_id`` 映射到对应的 ``lottery.*_next_time`` 配置项，并通过统一配置
    读取函数获取其值。未找到映射、读取失败或配置不存在时返回空字符串。

    Args:
        db_path (str | Path): 数据库路径或连接配置路径。
        lottery_type_id (int): 彩种 ID，当前约定 1 为香港彩、2 为澳门彩、3 为台湾彩。

    Returns:
        str: 彩种下一期开奖时间字符串；读取失败或不存在时返回空字符串。
    """
    config_key = LOTTERY_NEXT_TIME_CONFIG_KEYS.get(lottery_type_id)
    if not config_key:
        return ""
    try:
        return str(get_config(db_path, config_key, ""))
    except Exception:
        return ""
