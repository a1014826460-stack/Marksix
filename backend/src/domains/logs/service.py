"""日志领域业务逻辑层（Service）。

错误日志查询、统计、导出、清理。
当前阶段委托给 logger.py 中的现有实现。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def query_error_logs(
    db_path: str | Path,
    *,
    level: str = "",
    module: str = "",
    keyword: str = "",
    page: int = 1,
    page_size: int = 30,
) -> dict[str, Any]:
    """分页查询错误日志。"""
    from logger import query_error_logs as _impl
    return _impl(
        db_path,
        level=level, module=module, keyword=keyword,
        page=page, page_size=page_size,
    )


def get_log_stats(db_path: str | Path) -> dict[str, Any]:
    """获取日志统计信息。"""
    from logger import get_log_stats as _impl
    return _impl(db_path)


def get_log_modules(db_path: str | Path) -> list[str]:
    """获取所有日志模块名。"""
    from db import connect
    from domains.logs.repository import get_distinct_modules
    with connect(db_path) as conn:
        return get_distinct_modules(conn)


def get_log_levels(db_path: str | Path) -> list[str]:
    """获取所有日志级别。"""
    from db import connect
    from domains.logs.repository import get_distinct_levels
    with connect(db_path) as conn:
        return get_distinct_levels(conn)


def get_log_detail(db_path: str | Path, log_id: int) -> dict[str, Any] | None:
    """查询单条日志详情。"""
    from db import connect
    from domains.logs.repository import find_log_by_id
    with connect(db_path) as conn:
        return find_log_by_id(conn, log_id)


def trigger_log_cleanup(db_path: str | Path) -> dict[str, Any]:
    """触发日志清理。"""
    from logger import trigger_cleanup as _impl
    return _impl(db_path)
