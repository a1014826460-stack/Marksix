"""预测机制注册表 —— 统一管理所有预测机制的加载和查询。

当前阶段委托给 predict.mechanisms 中的现有实现。
后续作为机制拆分的中心注册入口。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def list_mechanisms(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    """列出所有可用预测机制。"""
    from predict.mechanisms import list_prediction_configs as _impl
    return _impl(db_path)


def get_mechanism(key: str) -> dict[str, Any]:
    """获取指定 key 的预测机制配置。"""
    from predict.mechanisms import get_prediction_config as _impl
    return _impl(key)


def set_status(key: str, status: int) -> None:
    """设置机制启用/停用状态。"""
    from predict.mechanism_status import set_mechanism_status as _impl
    _impl(key, status)


def ensure_loaded(db_path: str | Path | None = None) -> None:
    """确保所有预测配置已加载。"""
    from predict.mechanisms import ensure_prediction_configs_loaded as _impl
    _impl(db_path)
