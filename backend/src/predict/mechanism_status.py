"""预测机制状态管理 —— 启用/禁用控制。

从 predict/mechanisms.py 中提取，供 routes 层和 predict_engine 层复用。
"""

from __future__ import annotations

from pathlib import Path

from db import connect as db_connect, utc_now


def get_mechanism_statuses(db_path: str | Path) -> dict[str, int]:
    """获取所有预测机制的启用/禁用状态映射。"""
    from db import connect
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT mechanism_key, status FROM mechanism_status"
        ).fetchall()
    return {str(row["mechanism_key"]): int(row["status"]) for row in rows}


def set_mechanism_status(db_path: str | Path, key: str, status: int) -> None:
    """设置预测机制的启用/禁用状态（status: 1=启用, 0=禁用）。"""
    now = utc_now()
    with db_connect(db_path) as conn:
        conn.execute(
            """INSERT INTO mechanism_status (mechanism_key, status, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(mechanism_key) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at""",
            (key, status, now),
        )
