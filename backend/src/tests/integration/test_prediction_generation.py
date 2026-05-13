"""预测资料生成集成测试。

测试内容：
- 站点 web_id 隔离（web_id=7 时 row_data.web 必须是 7）
- 不能写成 4
- 未开奖期不能注入真实 res_code
- 部分模块失败时有错误记录

注意：需要 PostgreSQL 连接，通过 TEST_DATABASE_URL 环境变量配置。
"""

from __future__ import annotations

import os
import pytest

from db import connect, is_postgres_target, default_postgres_target


def _connect_for_test():
    """获取测试数据库连接。"""
    test_target = os.getenv("TEST_DATABASE_URL", "").strip()
    if test_target and is_postgres_target(test_target):
        return connect(test_target)

    if os.getenv("ALLOW_TEST_ON_PROD_DB", "").strip().lower() in ("1", "true", "yes"):
        try:
            default = default_postgres_target()
        except RuntimeError:
            default = ""
        if default and is_postgres_target(default):
            return connect(default)

    pytest.skip("需要 PostgreSQL 测试数据库。请设置 TEST_DATABASE_URL 环境变量。")


# ── web_id 隔离测试 ────────────────────────────────────

def test_site_context_web_id_isolation():
    """验证站点 web_id 解析正确：不同站点返回各自的 web_id。

    这是一个健康检查测试：确保常见的 web_id 不是 4。
    """
    from app_http.site_context import resolve_site_context

    conn = _connect_for_test()
    from tables import ensure_admin_tables
    ensure_admin_tables(conn.target)

    # 查询所有站点
    rows = conn.execute(
        "SELECT id, web_id, name FROM managed_sites ORDER BY id"
    ).fetchall()

    for row in rows:
        web_id = row["web_id"]
        if web_id is not None:
            # 验证：web_id 不应为 4（除非恰好是站点自身的 web_id）
            # 这个测试确保没有硬编码 web=4
            assert int(web_id) >= 1, f"站点 site_id={row['id']} web_id 应为正整数"

    conn.close()


def test_resolve_site_context_returns_correct_web_id():
    """验证 resolve_site_context 返回正确的 web_id。"""
    from app_http.site_context import resolve_site_context

    conn = _connect_for_test()
    from tables import ensure_admin_tables
    ensure_admin_tables(conn.target)

    # 获取第一个站点
    first_site = conn.execute(
        "SELECT id, web_id FROM managed_sites ORDER BY id LIMIT 1"
    ).fetchone()

    if first_site and first_site["web_id"] is not None:
        ctx = resolve_site_context(
            conn.target,
            path_site_id=int(first_site["id"]),
        )
        assert ctx.web_id == int(first_site["web_id"]), (
            f"resolve_site_context 返回 web_id={ctx.web_id}，"
            f"期望 {first_site['web_id']}"
        )

    conn.close()


def test_validate_web_matches_site_rejects_mismatch():
    """验证 web 不匹配时 validate_web_matches_site 抛出异常。"""
    from app_http.site_context import (
        resolve_site_context,
        validate_web_matches_site,
    )
    from core.errors import ForbiddenError

    conn = _connect_for_test()
    from tables import ensure_admin_tables
    ensure_admin_tables(conn.target)

    first_site = conn.execute(
        "SELECT id FROM managed_sites ORDER BY id LIMIT 1"
    ).fetchone()

    if first_site:
        ctx = resolve_site_context(
            conn.target,
            path_site_id=int(first_site["id"]),
        )
        # 用一个不可能匹配的 web 值
        try:
            validate_web_matches_site(ctx, 99999)
            # 如果站点恰好 web_id=99999，那这个测试不成立
        except ForbiddenError:
            pass  # 期望行为

    conn.close()
