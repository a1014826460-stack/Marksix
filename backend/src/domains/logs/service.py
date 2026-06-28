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
    date_from: str = "",
    date_to: str = "",
    user_id: str = "",
    site_id: str = "",
    web_id: str = "",
    lottery_type_id: str = "",
    year: str = "",
    term: str = "",
    task_type: str = "",
    task_key: str = "",
    path: str = "",
    page: int = 1,
    page_size: int = 30,
) -> dict[str, Any]:
    """分页查询错误日志。"""
    from logger import query_error_logs as _impl
    return _impl(
        db_path,
        level=level, module=module, keyword=keyword,
        date_from=date_from, date_to=date_to,
        user_id=user_id, site_id=site_id, web_id=web_id,
        lottery_type_id=lottery_type_id, year=year, term=term,
        task_type=task_type, task_key=task_key, path=path,
        page=page, page_size=page_size,
    )


def export_error_logs(
    db_path: str | Path,
    *,
    level: str = "",
    module: str = "",
    keyword: str = "",
    date_from: str = "",
    date_to: str = "",
) -> list[dict[str, Any]]:
    """导出错误日志。"""
    from logger import export_error_logs as _impl

    return _impl(
        db_path,
        level=level,
        module=module,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
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


def query_backfill_logs(
    db_path: str | Path,
    *,
    lottery_type_id: int | None = None,
    period: str = "",
    action: str = "",
    date_from: str = "",
    date_to: str = "",
    page: int = 1,
    page_size: int = 30,
) -> dict[str, Any]:
    """查询 prediction.backfill 事件日志。"""
    from db import connect
    from domains.logs.repository import query_backfill_logs as _query_backfill_logs

    with connect(db_path) as conn:
        rows, total = _query_backfill_logs(
            conn,
            lottery_type_id=lottery_type_id,
            period=period,
            action=action,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )
    return {
        "items": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


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
