"""Configuration loader — reads config.yaml and provides defaults.

Design choice: we keep a minimal YAML parser (stdlib only) instead of
depending on pyyaml, because the config is simple nested dicts and the
rest of the project aims to minimise third-party dependencies.

If the config file is missing or partially unreadable, sensible defaults
are returned so the server can still start.
"""

from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Any

CONFIG_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = CONFIG_DIR / "config.yaml"


def _parse_yaml(text: str) -> dict[str, Any]:
    """Parse a minimal YAML subset: nested mappings (2-level), comments, quoted strings."""
    result: dict[str, Any] = {}
    current_section: str | None = None
    section_pattern = re.compile(r"^(\w+):\s*$")
    kv_pattern = re.compile(r"^\s{2}(\w[\w_]*):\s*(.*)")
    quoted = re.compile(r'^"((?:[^"\\]|\\.)*)"\s*$')

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        m = section_pattern.match(stripped)
        if m:
            current_section = m.group(1)
            result.setdefault(current_section, {})
            continue

        if current_section is not None:
            m = kv_pattern.match(line)
            if m:
                key = m.group(1)
                raw = m.group(2).strip()
                # Remove surrounding quotes
                qm = quoted.match(raw)
                if qm:
                    raw = qm.group(1)
                if raw == "''" or raw == '""':
                    raw = ""
                elif raw.startswith("[") and raw.endswith("]"):
                    try:
                        raw = json.loads(raw)
                    except json.JSONDecodeError:
                        pass
                elif raw.lower() == "true":
                    raw = True
                elif raw.lower() == "false":
                    raw = False
                else:
                    try:
                        if "." in raw:
                            raw = float(raw)
                        else:
                            raw = int(raw)
                    except (ValueError, TypeError):
                        pass
                result[current_section][key] = raw  # type: ignore[index]

    return result


def _merge_defaults(loaded: dict[str, Any]) -> dict[str, Any]:
    """Fill in any missing keys with defaults so callers never KeyError."""
    defaults: dict[str, dict[str, Any]] = {
        "database": {
            "default_postgres_dsn": "postgresql://postgres:2225427@localhost:5432/liuhecai",
        },
        "admin": {
            "username": "admin",
            "password": "admin123",
            "display_name": "系统管理员",
            "role": "super_admin",
        },
        "auth": {
            "session_ttl_seconds": 86400,
            "password_iterations": 260000,
        },
        "fetch_site": {
            "manage_url_template": "https://admin.shengshi8800.com/ds67BvM/web/webManage?id={web_id}",
            "modes_data_url": "https://admin.shengshi8800.com/ds67BvM/web/getModesDataList",
            "default_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiIiLCJhdWQiOiIiLCJpYXQiOjE3NzgxNTQyMzEsIm5iZiI6MTc3ODE1NDIzNCwiZXhwIjoxNzc4MjQwNjMxLCJkYXRhIjp7ImlkIjoxLCJuYW1lIjoiYWRtaW4iLCJzaWduIjoiXHU4ZDg1XHU3ZWE3XHU3YmExXHU3NDA2XHU1NDU4IiwianVyIjpudWxsfX0.1IaOuliRxxiil00NGadmiRii1XTb9u-HsdXKJLH-I04",
            "default_site_name": "默认盛世站点",
            "default_domain": "admin.shengshi8800.com",
            "start_web_id": 1,
            "end_web_id": 10,
            "request_limit": 250,
            "request_delay": 0.5,
            "default_announcement": "欢迎使用彩票网站数据管理后台。",
            "default_notes": "系统内置默认抓取配置，可在管理后台修改 token 和接口地址。",
        },
        "fetch": {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
        "crawler": {
            "interval_seconds": 3600,
            "http_timeout_seconds": 30,
            "http_retry_count": 2,
            "http_retry_delay_seconds": 1.0,
            "auto_open_interval_seconds": 60,
            "auto_crawl_interval_seconds": 600,
            "auto_crawl_recent_minutes": 30,
            "auto_prediction_delay_hours": 6,
            "task_poll_interval_seconds": 30,
            "task_lock_timeout_seconds": 300,
            "task_retry_delay_seconds": 60,
            "taiwan_precise_open_hour": 22,
            "taiwan_precise_open_minute": 30,
            "taiwan_retry_delays_seconds": [60, 300, 900],
            "taiwan_max_retries": 3,
            "message_hk_empty_data": "API returned no Hong Kong draw data.",
            "message_macau_empty_data": "API returned no Macau draw data.",
            "message_taiwan_import_only": "Taiwan data must be imported from JSON.",
        },
        "draw": {
            "hk_default_draw_time": "21:30",
            "macau_default_draw_time": "21:30",
            "taiwan_default_draw_time": "22:30",
            "hk_default_collect_url": "https://www.lnlllt.com/api.php",
            "macau_default_collect_url": "https://www.lnlllt.com/api.php",
            "taiwan_import_file": "data/lottery_data/lottery_page_1_20260506_194209.json",
        },
        "prediction": {
            "default_target_hit_rate": 0.7,
            "max_terms_per_year": 365,
        },
        "logging": {
            "max_file_size_mb": 10,
            "backup_count": 10,
            "error_retention_days": 30,
            "warn_retention_days": 7,
            "info_retention_days": 3,
            "max_total_log_size_mb": 500,
            "cleanup_interval_seconds": 3600,
            "slow_call_warning_ms": 5000,
        },
        "legacy": {
            "images_dir": "data/Images",
            "images_upload_bucket": "20250322",
            "post_list_pc": 305,
            "post_list_web": 4,
            "post_list_type": 3,
        },
    }
    for section, keys in defaults.items():
        if section not in loaded:
            loaded[section] = {}
        for key, default_value in keys.items():
            loaded[section].setdefault(key, default_value)
    return loaded


_config: dict[str, Any] | None = None


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load and cache config from the given path (or the default)."""
    global _config
    if _config is not None:
        return _config

    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    loaded: dict[str, Any] = {}

    if config_path.exists():
        text = config_path.read_text(encoding="utf-8")
        loaded = _parse_yaml(text)

    _config = _merge_defaults(loaded)
    return _config


def get_config() -> dict[str, Any]:
    """Return the cached config, loading it on first call."""
    if _config is None:
        return load_config()
    return _config


# Convenience accessors
def get(key: str, default: Any = None) -> Any:
    """Get a top-level config value."""
    return get_config().get(key, default)


def section(name: str) -> dict[str, Any]:
    """Get a config section dict."""
    return get_config().get(name, {})
