"""预测机制状态管理 —— 启用/禁用控制。

从 predict/mechanisms.py 中提取，供 routes 层和 predict_engine 层复用。
"""

from __future__ import annotations

from pathlib import Path

from db import connect as db_connect, utc_now
from domains.prediction import state_repository


def get_mechanism_statuses(db_path: str | Path) -> dict[str, int]:
    """获取所有预测机制的启用/禁用状态映射。"""
    with db_connect(db_path) as conn:
        return state_repository.get_mechanism_statuses(conn)


def set_mechanism_status(db_path: str | Path, key: str, status: int) -> None:
    """设置预测机制的启用/禁用状态（status: 1=启用, 0=禁用）。"""
    now = utc_now()
    with db_connect(db_path) as conn:
        state_repository.set_mechanism_status(conn, key, status, updated_at=now)
