"""测试配置和共享 fixtures。

集成测试需要 PostgreSQL 连接；无数据库时自动跳过。

导入路径：pytest 运行时会优先把 backend/src/ 加入 sys.path，
确保所有模块（core, app_http, routes, domains 等）能正常导入，
不依赖 app.py 的副作用。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# 确保 backend/src/ 在 sys.path 中，所有测试模块可直接导入
_SRC_ROOT = Path(__file__).resolve().parents[1]
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

import pytest

from db import connect, is_postgres_target, resolve_database_target


def _get_test_db_target() -> str:
    """获取测试数据库目标，优先级：环境变量 > 默认值。"""
    env_target = os.getenv("TEST_DATABASE_URL", "").strip()
    if env_target:
        return env_target
    # 尝试使用正式数据库（仅集成测试场景）
    default = os.getenv("DATABASE_URL", "").strip()
    if default and is_postgres_target(default):
        return default
    return ""


TEST_DB_TARGET = _get_test_db_target()
HAS_TEST_DB = bool(TEST_DB_TARGET) and is_postgres_target(TEST_DB_TARGET)

requires_test_db = pytest.mark.skipif(
    not HAS_TEST_DB,
    reason="需要 PostgreSQL 测试数据库。请设置 TEST_DATABASE_URL 环境变量。",
)


@pytest.fixture(scope="module")
def db_conn():
    """模块级数据库连接 fixture（集成测试用）。"""
    if not HAS_TEST_DB:
        pytest.skip("无可用测试数据库")
    target = resolve_database_target(TEST_DB_TARGET)
    with connect(target) as conn:
        yield conn


@pytest.fixture(scope="module")
def db_path() -> str:
    """返回测试数据库路径。"""
    if not HAS_TEST_DB:
        pytest.skip("无可用测试数据库")
    return str(resolve_database_target(TEST_DB_TARGET))
