"""配置领域业务逻辑层（Service）。

配置读取、更新、校验、历史查询。
当前阶段委托给 runtime_config 中的现有实现。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def list_configs(db_path: str | Path, prefix: str = "", include_secrets: bool = False) -> list[dict[str, Any]]:
    """列出配置（支持前缀筛选和敏感值隐藏）。"""
    from runtime_config import list_system_configs
    return list_system_configs(db_path, prefix=prefix, include_secrets=include_secrets)


def get_effective_configs(db_path: str | Path, group: str = "", keyword: str = "", source: str = "") -> list[dict[str, Any]]:
    """查询所有配置项的实际生效值列表。"""
    from runtime_config import list_configs_effective
    return list_configs_effective(db_path, group=group, keyword=keyword, source=source)


def get_config_effective(db_path: str | Path, key: str) -> dict[str, Any]:
    """查询单个配置项的实际生效值及来源。"""
    from runtime_config import get_config_effective
    return get_config_effective(db_path, key)


def get_config_groups() -> list[dict[str, Any]]:
    """返回配置分组定义。"""
    from runtime_config import get_config_groups
    return get_config_groups()


def upsert_config(
    db_path: str | Path, key: str, value: Any, value_type: str | None = None,
    description: str | None = None, is_secret: bool | None = None,
    changed_by: str = "", change_reason: str = "",
) -> dict[str, Any]:
    """更新或插入配置项。"""
    from runtime_config import upsert_system_config
    return upsert_system_config(
        db_path, key=key, value=value, value_type=value_type,
        description=description, is_secret=is_secret,
        changed_by=changed_by, change_reason=change_reason,
    )


def batch_update_configs(db_path: str | Path, updates: list[dict[str, Any]], changed_by: str = "") -> dict[str, Any]:
    """批量更新配置项。"""
    from runtime_config import batch_update_configs
    return batch_update_configs(db_path, updates, changed_by=changed_by)


def reset_config(db_path: str | Path, key: str, changed_by: str = "") -> dict[str, Any]:
    """将配置项恢复为默认值。"""
    from runtime_config import reset_config
    return reset_config(db_path, key, changed_by=changed_by)


def get_config_history(db_path: str | Path, key: str = "", page: int = 1, page_size: int = 30) -> dict[str, Any]:
    """分页查询配置变更历史。"""
    from runtime_config import get_config_history
    return get_config_history(db_path, key=key, page=page, page_size=page_size)


def validate_config_value(key: str, value: Any, value_type: str) -> tuple[bool, str]:
    """校验配置值类型及基础业务约束。"""
    from runtime_config import validate_config_value
    return validate_config_value(key, value, value_type)
