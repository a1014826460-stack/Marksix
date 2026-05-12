"""旧站兼容领域业务逻辑层。

旧版 post-list、current-term、module-rows 等 API 的业务逻辑封装。
当前阶段委托给 legacy/api.py 中的现有实现。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def list_post_images(
    db_path: str | Path,
    *,
    source_pc: int | None = None,
    source_web: int | None = None,
    source_type: int | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """获取旧版首页图片卡片列表。"""
    from legacy.api import list_legacy_post_images
    return list_legacy_post_images(
        db_path, source_pc=source_pc, source_web=source_web,
        source_type=source_type, limit=limit,
    )


def get_current_term(
    db_path: str | Path,
    lottery_type_id: int,
    *,
    pc: int | None = None,
    web: int | None = None,
    type_val: int | None = None,
) -> dict[str, Any]:
    """获取旧版当前期号信息。"""
    from legacy.api import get_legacy_current_term
    return get_legacy_current_term(
        db_path, lottery_type_id, pc=pc, web=web, type_val=type_val,
    )


def get_module_rows(
    db_path: str | Path,
    *,
    modes_id: int,
    pc: int | None = None,
    web: int | None = None,
    type_val: int | None = None,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """获取旧版模块行数据。"""
    from legacy.api import load_legacy_mode_rows
    return load_legacy_mode_rows(
        db_path, modes_id=modes_id, pc=pc, web=web,
        type_val=type_val, limit=limit,
    )
