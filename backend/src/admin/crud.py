"""
Admin CRUD 操作模块 —— 托管站点、管理员用户、彩种、开奖记录、号码数据的增删改查。

从 app.py 中提取，将 HTTP 路由与数据访问逻辑分离。所有函数保持原有的
签名、函数体和文档字符串不变，仅新增规范的中文注释（含 param / return / raises）。

Extracted from app.py to provide a clean separation between HTTP routing
and data-access logic. All functions preserve their original signatures,
bodies, and docstrings exactly as they appear in app.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tables import ensure_admin_tables

_ORIGINAL_ENSURE_ADMIN_TABLES = ensure_admin_tables






# ─────────────────────────────────────────────────────────────────
#  站点 CRUD / Site CRUD
# ─────────────────────────────────────────────────────────────────

def public_site(row: Any) -> dict[str, Any]:
    """将数据库中的站点行转换为对外安全的字典（隐藏完整 token）。

    委托给 domains/sites/service.py 的统一实现。
    """
    from domains.sites.service import public_site as _impl
    return _impl(row)


def list_sites(db_path: str | Path) -> list[dict[str, Any]]:
    """获取所有托管站点列表。

    委托给 domains/sites/service.py 的统一实现。
    """
    from domains.sites.service import list_sites as _impl
    return _impl(db_path)


def get_site(db_path: str | Path, site_id: int, include_secret: bool = False) -> dict[str, Any]:
    """根据 ID 获取单个托管站点的详细信息。

    委托给 domains/sites/service.py 的统一实现。
    """
    from domains.sites.service import get_site as _impl
    return _impl(db_path, site_id, include_secret)


def save_site(db_path: str | Path, payload: dict[str, Any], site_id: int | None = None) -> dict[str, Any]:
    """创建或更新托管站点。

    委托给 domains/sites/service.py 的统一实现。
    """
    from domains.sites.service import save_site as _impl
    return _impl(db_path, payload, site_id)


def delete_site(db_path: str | Path, site_id: int) -> None:
    """删除指定 ID 的托管站点。

    委托给 domains/sites/service.py 的统一实现。
    """
    from domains.sites.service import delete_site as _impl
    return _impl(db_path, site_id)


# ─────────────────────────────────────────────────────────────────
#  管理员用户 CRUD / User CRUD
# ─────────────────────────────────────────────────────────────────

def list_users(db_path: str | Path) -> list[dict[str, Any]]:
    """Compatibility wrapper for the users domain service."""
    from domains.users.service import list_users as _impl

    return _impl(db_path)

def save_user(db_path: str | Path, payload: dict[str, Any], user_id: int | None = None) -> dict[str, Any]:
    """Compatibility wrapper for the users domain service."""
    from domains.users.service import save_user as _impl

    return _impl(db_path, payload, user_id=user_id)

def delete_user(db_path: str | Path, user_id: int) -> None:
    """Compatibility wrapper for the users domain service."""
    from domains.users.service import delete_user as _impl

    return _impl(db_path, user_id)

# ─────────────────────────────────────────────────────────────────
#  彩种 CRUD / Lottery Type CRUD
# ─────────────────────────────────────────────────────────────────

def list_lottery_types(db_path: str | Path) -> list[dict[str, Any]]:
    """Compatibility wrapper for the lottery domain service."""
    from domains.lottery import service as _service

    return _call_lottery_service(_service.list_lottery_types, db_path)


def save_lottery_type(db_path: str | Path, payload: dict[str, Any], lottery_id: int | None = None) -> dict[str, Any]:
    """Compatibility wrapper for the lottery domain service."""
    from domains.lottery import service as _service

    return _call_lottery_service(_service.save_lottery_type, db_path, payload, lottery_id=lottery_id)

def delete_lottery_type(db_path: str | Path, lottery_id: int) -> None:
    """Compatibility wrapper for the lottery domain service."""
    from domains.lottery import service as _service

    return _call_lottery_service(_service.delete_lottery_type, db_path, lottery_id)


def _call_lottery_service(func: Any, *args: Any, **kwargs: Any) -> Any:
    """Preserve the legacy admin.crud.ensure_admin_tables patch point."""
    if ensure_admin_tables is _ORIGINAL_ENSURE_ADMIN_TABLES:
        return func(*args, **kwargs)

    from domains.lottery import service as _service

    original = _service.ensure_admin_tables
    _service.ensure_admin_tables = ensure_admin_tables
    try:
        return func(*args, **kwargs)
    finally:
        _service.ensure_admin_tables = original

# ─────────────────────────────────────────────────────────────────
#  开奖记录 CRUD / Draw CRUD
# ─────────────────────────────────────────────────────────────────

def list_draws(
    db_path: str | Path,
    limit: int = 200,
    offset: int = 0,
    lottery_type_id: int | None = None,
) -> dict[str, Any]:
    """Compatibility wrapper for the lottery domain service."""
    from domains.lottery import service as _service

    return _call_lottery_service(
        _service.list_draws,
        db_path,
        limit=limit,
        offset=offset,
        lottery_type_id=lottery_type_id,
    )


def save_draw(db_path: str | Path, payload: dict[str, Any], draw_id: int | None = None) -> dict[str, Any]:
    """Compatibility wrapper for the lottery domain service."""
    from domains.lottery import service as _service

    return _call_lottery_service(_service.save_draw, db_path, payload, draw_id=draw_id)

def delete_draw(db_path: str | Path, draw_id: int) -> None:
    """Compatibility wrapper for the lottery domain service."""
    from domains.lottery import service as _service

    return _call_lottery_service(_service.delete_draw, db_path, draw_id)

# ─────────────────────────────────────────────────────────────────
#  号码 CRUD（操作 fixed_data 表）
#  Number CRUD (operates on fixed_data)
# ─────────────────────────────────────────────────────────────────

def list_numbers(db_path: str | Path, limit: int = 300, keyword: str = "", sign: str = "") -> list[dict[str, Any]]:
    """Compatibility wrapper for the numbers domain service."""
    from domains.numbers.service import list_numbers as _impl

    return _impl(db_path, limit=limit, keyword=keyword, sign=sign)

def update_number(db_path: str | Path, number_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Compatibility wrapper for the numbers domain service."""
    from domains.numbers.service import update_number as _impl

    return _impl(db_path, number_id, payload)

def create_number(db_path: str | Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Compatibility wrapper for the numbers domain service."""
    from domains.numbers.service import create_number as _impl

    return _impl(db_path, payload)

def delete_number(db_path: str | Path, number_id: int) -> None:
    """Compatibility wrapper for the numbers domain service."""
    from domains.numbers.service import delete_number as _impl

    return _impl(db_path, number_id)

# ─────────────────────────────────────────────────────────────────
#  站点预测模块 CRUD / Site prediction module CRUD
#  DEPRECATED: 已迁移到 domains/prediction/service.py。
#  以下函数不再被新代码调用，保留仅供向后兼容。
#  新代码请使用 domains.prediction.service 中的对应函数。
# ─────────────────────────────────────────────────────────────────

def list_site_prediction_modules(db_path: str | Path, site_id: int) -> dict[str, Any]:
    from domains.prediction import service as _prediction_service

    return _prediction_service.list_site_prediction_modules(db_path, site_id)

def add_site_prediction_module(
    db_path: str | Path, site_id: int, payload: dict[str, Any]
) -> dict[str, Any]:
    from domains.prediction import service as _prediction_service

    return _prediction_service.add_site_prediction_module(db_path, site_id, payload)

def update_site_prediction_module(
    db_path: str | Path, site_id: int, module_id: int, payload: dict[str, Any]
) -> dict[str, Any]:
    from domains.prediction import service as _prediction_service

    return _prediction_service.update_site_prediction_module(db_path, site_id, module_id, payload)

def delete_site_prediction_module(db_path: str | Path, site_id: int, module_id: int) -> None:
    from domains.prediction import service as _prediction_service

    return _prediction_service.delete_site_prediction_module(db_path, site_id, module_id)

def run_site_prediction_module(db_path: str | Path, site_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    from domains.prediction import service as _prediction_service

    return _prediction_service.run_prediction(db_path, site_id, payload)
