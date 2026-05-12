"""预测领域业务逻辑层（Service）。

预测模块管理、预测资料批量生成、未开奖安全判断。
当前阶段委托给现有 admin/crud.py 和 admin/prediction.py。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def list_site_prediction_modules(db_path: str | Path, site_id: int) -> dict[str, Any]:
    """获取指定站点的预测模块列表。"""
    from admin.crud import list_site_prediction_modules as _impl
    return _impl(db_path, site_id)


def add_site_prediction_module(db_path: str | Path, site_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """为站点添加预测模块。"""
    from admin.crud import add_site_prediction_module as _impl
    return _impl(db_path, site_id, payload)


def update_site_prediction_module(
    db_path: str | Path, site_id: int, module_id: int, payload: dict[str, Any]
) -> dict[str, Any]:
    """更新站点预测模块。"""
    from admin.crud import update_site_prediction_module as _impl
    return _impl(db_path, site_id, module_id, payload)


def delete_site_prediction_module(db_path: str | Path, site_id: int, module_id: int) -> None:
    """删除站点预测模块。"""
    from admin.crud import delete_site_prediction_module as _impl
    return _impl(db_path, site_id, module_id)


def run_prediction(db_path: str | Path, site_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """执行一次预测运算。"""
    from admin.crud import run_site_prediction_module as _impl
    return _impl(db_path, site_id, payload)


def sync_site_prediction_modules(db_path: str | Path, site_id: int) -> None:
    """同步站点预测模块（补齐缺失的机制）。"""
    from admin.prediction import sync_site_prediction_modules as _impl
    from db import connect
    with connect(db_path) as conn:
        _impl(conn, site_id=site_id)


def bulk_generate_site_predictions(
    db_path: str | Path,
    *,
    site_id: int,
    start_year: int,
    start_term: int,
    end_year: int,
    end_term: int,
    mechanism_keys: list[str] | None = None,
    created_by: str = "",
) -> dict[str, Any]:
    """批量生成站点预测资料。

    委托给 admin/prediction.py 中的 bulk_generate_site_prediction_data。
    """
    from admin.prediction import bulk_generate_site_prediction_data as _impl
    return _impl(
        db_path,
        site_id=site_id,
        start_year=start_year,
        start_term=start_term,
        end_year=end_year,
        end_term=end_term,
        mechanism_keys=mechanism_keys,
        created_by=created_by,
    )
