"""数据库 bootstrap 集成测试。

测试内容：
- 空 PostgreSQL 数据库可以初始化
- 重复初始化幂等
- managed_sites.web_id 存在
- scheduler_tasks 上下文字段存在
- error_logs 上下文字段存在
- 索引存在

注意：需要 PostgreSQL 连接，通过 TEST_DATABASE_URL 环境变量配置。
"""

from __future__ import annotations

import os
import pytest
from pathlib import Path

from db import connect, is_postgres_target, resolve_database_target, default_postgres_target


def _connect_for_test():
    """获取测试数据库连接（使用独立测试数据库避免破坏正式数据）。"""
    # 优先使用专用测试数据库
    test_target = os.getenv("TEST_DATABASE_URL", "").strip()
    if test_target and is_postgres_target(test_target):
        return connect(test_target)

    # 回退：使用正式数据库但跳过危险测试
    default = default_postgres_target()
    if default and is_postgres_target(default):
        # 仅在明确许可时使用正式数据库
        if os.getenv("ALLOW_TEST_ON_PROD_DB", "").strip().lower() in ("1", "true", "yes"):
            return connect(default)

    pytest.skip("需要 PostgreSQL 测试数据库。请设置 TEST_DATABASE_URL 环境变量。")


# ── bootstrap 测试 ─────────────────────────────────────

def test_ensure_admin_tables_idempotent():
    """验证 ensure_admin_tables 可以安全重复调用（幂等）。"""
    from tables import ensure_admin_tables

    conn = _connect_for_test()
    db_path = conn.target

    # 第一次调用
    ensure_admin_tables(db_path)

    # 第二次调用不应抛异常
    ensure_admin_tables(db_path)
    conn.close()


def test_managed_sites_web_id_exists():
    """验证 managed_sites 表有 web_id 列，且已有站点被回填。"""
    conn = _connect_for_test()
    # 确保表已初始化
    from tables import ensure_admin_tables
    ensure_admin_tables(conn.target)

    columns = conn.table_columns("managed_sites")
    assert "web_id" in columns, f"managed_sites 缺少 web_id 列，现有列: {columns}"

    # 检查是否已有站点且 web_id 不为空
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM managed_sites WHERE web_id IS NULL"
    ).fetchone()
    null_count = int(row["cnt"] or 0)
    assert null_count == 0, f"存在 {null_count} 个站点的 web_id 为 NULL，需要回填"

    conn.close()


def test_scheduler_tasks_context_columns():
    """验证 scheduler_tasks 表存在业务上下文字段。"""
    conn = _connect_for_test()
    from tables import ensure_admin_tables
    ensure_admin_tables(conn.target)

    columns = set(conn.table_columns("scheduler_tasks"))
    required = {"site_id", "web_id", "lottery_type_id", "year", "term", "created_by"}
    missing = required - columns
    assert not missing, f"scheduler_tasks 缺少业务上下文字段: {missing}"

    conn.close()


def test_error_logs_context_columns():
    """验证 error_logs 表存在业务上下文字段。"""
    conn = _connect_for_test()
    from tables import ensure_admin_tables
    ensure_admin_tables(conn.target)

    columns = set(conn.table_columns("error_logs"))
    required = {"site_id", "web_id", "lottery_type_id", "year", "term", "task_key", "task_type"}
    missing = required - columns
    assert not missing, f"error_logs 缺少业务上下文字段: {missing}"

    conn.close()


def test_indexes_exist():
    """验证关键索引存在。"""
    conn = _connect_for_test()
    from tables import ensure_admin_tables
    ensure_admin_tables(conn.target)

    # PostgreSQL 中查询索引名
    if conn.engine == "postgres":
        rows = conn.execute(
            """
            SELECT indexname FROM pg_indexes
            WHERE schemaname = current_schema()
            """
        ).fetchall()
        index_names = {str(row["indexname"]) for row in rows}
    else:
        # SQLite: 从 sqlite_master 查询
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index'"
        ).fetchall()
        index_names = {str(row[0]) for row in rows}

    expected = [
        "idx_lottery_draws_type_opened_issue",
        "idx_managed_sites_web_id",
        "idx_scheduler_tasks_status_run_at",
        "idx_error_logs_created_level_module",
    ]
    for idx_name in expected:
        assert idx_name in index_names, f"索引 {idx_name} 未创建"

    conn.close()
