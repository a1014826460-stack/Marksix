"""Configuration loader — reads config.yaml and provides defaults.

Design choice: we keep a minimal YAML parser (stdlib only) instead of
depending on pyyaml, because the config is simple nested dicts and the
rest of the project aims to minimise third-party dependencies.

If the config file is missing or partially unreadable, sensible defaults
are returned so the server can still start.
"""

from __future__ import annotations

import os
import re
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
                # Empty string
                if raw == "''" or raw == '""':
                    raw = ""
                # Boolean
                if raw.lower() == "true":
                    raw = True
                elif raw.lower() == "false":
                    raw = False
                # Number
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
        },
        "site": {
            "manage_url_template": "https://admin.shengshi8800.com/ds67BvM/web/webManage?id={web_id}",
            "modes_data_url": "https://admin.shengshi8800.com/ds67BvM/web/getModesDataList",
            "default_token": "",
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
