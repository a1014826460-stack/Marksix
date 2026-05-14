"""彩种领域业务逻辑层（Service）。

彩种管理、开奖数据管理、最新开奖查询。
当前阶段委托给 admin/crud.py 中的现有实现。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def list_lottery_types(db_path: str | Path) -> list[dict[str, Any]]:
    """获取所有彩种列表。"""
    from admin.crud import list_lottery_types as _impl
    return _impl(db_path)


def save_lottery_type(db_path: str | Path, payload: dict[str, Any], lottery_id: int | None = None) -> dict[str, Any]:
    """创建或更新彩种。"""
    from admin.crud import save_lottery_type as _impl
    return _impl(db_path, payload, lottery_id)


def delete_lottery_type(db_path: str | Path, lottery_id: int) -> None:
    """删除指定彩种。"""
    from admin.crud import delete_lottery_type as _impl
    return _impl(db_path, lottery_id)


def get_latest_draw(db_path: str | Path, lottery_type_id: int) -> dict[str, Any] | None:
    """获取指定彩种最新一期已开奖记录。"""
    from db import connect
    from domains.lottery.repository import find_latest_draw
    with connect(db_path) as conn:
        return find_latest_draw(conn, lottery_type_id)


def list_draws(db_path: str | Path, limit: int = 200, offset: int = 0, lottery_type_id: int | None = None) -> dict[str, Any]:
    """获取开奖记录列表（分页）。"""
    from admin.crud import list_draws as _impl
    return _impl(db_path, limit=limit, offset=offset, lottery_type_id=lottery_type_id)


def save_draw(db_path: str | Path, payload: dict[str, Any], draw_id: int | None = None) -> dict[str, Any]:
    """创建或更新开奖记录。"""
    from admin.crud import save_draw as _impl
    return _impl(db_path, payload, draw_id)


def delete_draw(db_path: str | Path, draw_id: int) -> None:
    """删除指定开奖记录。"""
    from admin.crud import delete_draw as _impl
    return _impl(db_path, draw_id)
