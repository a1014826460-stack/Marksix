"""Router 单元测试。

测试路由匹配优先级、更具体路由优先、404 等场景。
"""

from __future__ import annotations

from unittest.mock import MagicMock

from http.request_context import RequestContext
from http.router import Router, Route


def _make_ctx(path: str, method: str = "GET") -> RequestContext:
    """创建一个 mock RequestContext。"""
    handler = MagicMock()
    handler.path = path
    handler.headers = {}
    handler.server.db_path = ":memory:"
    ctx = RequestContext(handler, method)
    # 覆盖 path 以匹配传入的 path（RequestContext 会处理尾部斜杠）
    ctx.path = path.rstrip("/") or "/"
    return ctx


# ── 路由注册与匹配 ────────────────────────────────────

def test_exact_path_match():
    router = Router()
    called = []

    router.add("GET", "/api/health", lambda ctx: called.append("health"))
    ctx = _make_ctx("/api/health")
    router.dispatch(ctx)
    assert called == ["health"]


def test_method_mismatch():
    router = Router()
    called = []

    router.add("POST", "/api/health", lambda ctx: called.append("health"))
    ctx = _make_ctx("/api/health", method="GET")
    # GET 不应匹配 POST 路由，dispatch 会返回 404
    router.dispatch(ctx)
    assert called == []


def test_regex_match():
    router = Router()
    called = []

    router.add_regex(None, r"^/api/admin/sites/\d+$", lambda ctx: called.append("site_detail"))
    ctx = _make_ctx("/api/admin/sites/42")
    router.dispatch(ctx)
    assert called == ["site_detail"]


def test_regex_no_match():
    router = Router()
    called = []

    router.add_regex(None, r"^/api/admin/sites/\d+$", lambda ctx: called.append("site_detail"))
    ctx = _make_ctx("/api/admin/sites/42/mode-payload/table")
    # 这个路径不应匹配 /api/admin/sites/\d+$ （因为有更多路径段）
    router.dispatch(ctx)
    assert called == []


def test_more_specific_route_matches_first_in_order():
    """验证更具体的路由通过注册顺序优先匹配（first-match 策略）。

    关键测试：/api/admin/sites/{id}/mode-payload/... 不会被
    /api/admin/sites/{id} 遮挡，因为后者使用 $ 结尾的 regex。
    """
    router = Router()
    calls = []

    # 模拟 admin_site_routes 的注册
    router.add_regex(None, r"^/api/admin/sites/\d+$", lambda ctx: calls.append("site_detail"))
    # 模拟 admin_payload_routes 的注册
    router.add_regex(None, r"^/api/admin/sites/\d+/mode-payload/[^/]+$", lambda ctx: calls.append("payload"))

    # 请求 payload 路径
    ctx = _make_ctx("/api/admin/sites/42/mode-payload/mode_payload_3")
    router.dispatch(ctx)
    assert calls == ["payload"], f"应该匹配 payload 路由而非 site_detail, 实际: {calls}"


def test_route_first_match_wins():
    """多个路由可能匹配时，先注册的优先。"""
    router = Router()
    calls = []

    router.add_regex(None, r"^/api/admin/sites/\d+", lambda ctx: calls.append("first"))
    router.add_regex(None, r"^/api/admin/sites/\d+/mode-payload", lambda ctx: calls.append("second"))

    # 第一个 regex 会匹配所有 /api/admin/sites/{id}... 的请求
    ctx = _make_ctx("/api/admin/sites/42/mode-payload/table")
    router.dispatch(ctx)
    assert calls == ["first"], "first-match 策略下先注册的应优先"


def test_guard_blocks_access():
    """guard 抛异常时阻止 handler 执行。"""
    from core.errors import UnauthorizedError

    router = Router()
    called = []

    router.add(
        "GET",
        "/api/admin/secret",
        lambda ctx: called.append("secret"),
        guard=lambda ctx: (_ for _ in ()).throw(UnauthorizedError("未登录")),
    )

    ctx = _make_ctx("/api/admin/secret")
    router.dispatch(ctx)
    assert called == [], "guard 应阻止 handler 执行"


def test_404_response():
    """未匹配任何路由时应返回 404。"""
    router = Router()
    ctx = _make_ctx("/api/nonexistent")
    router.dispatch(ctx)
    # dispatch 会调用 ctx.send_error_json
    # mock handler 的 send_response 已被 response.py 设置
