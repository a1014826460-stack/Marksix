"""数据库连接相关函数的封装导出。

当前阶段从 db.py 直接导入，避免重复实现。
后续可将连接池、读写分离等逻辑集中到这里。
"""

from __future__ import annotations

from db import (  # noqa: F401 - 兼容导出
    auto_increment_primary_key,
    connect,
    ConnectionAdapter,
    CursorAdapter,
    default_postgres_target,
    DEFAULT_POSTGRES_DSN,
    detect_database_engine,
    is_postgres_target,
    quote_identifier,
    resolve_database_target,
    utc_now,
)


def default_db_target() -> str:
    """返回正式运行使用的 PostgreSQL 目标 DSN。"""
    return default_postgres_target()
