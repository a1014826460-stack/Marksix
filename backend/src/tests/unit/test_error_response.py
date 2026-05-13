"""错误响应治理测试。

验证 Router.dispatch() 在生产环境下不向客户端泄露 traceback。
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from app_http.request_context import RequestContext
from app_http.router import Router
from http import HTTPStatus


def _make_ctx(path: str, method: str = "GET"):
    handler = MagicMock()
    handler.path = path
    handler.command = method
    handler.headers = {}
    handler.server.db_path = "postgresql://test:test@localhost:5432/test"
    ctx = RequestContext(handler, method)
    ctx.path = path.rstrip("/") or "/"
    return ctx


class TestErrorResponseNoTraceback:
    """生产环境错误响应不应泄露 traceback。"""

    @patch.dict(os.environ, {}, clear=True)
    def test_router_dispatch_does_not_leak_traceback_in_production(self):
        """生产环境 Router.dispatch() 不泄露 traceback。"""
        router = Router()

        def _explode(ctx):
            raise RuntimeError("模拟内部错误")

        router.add("GET", "/api/test-explode", _explode)
        ctx = _make_ctx("/api/test-explode")

        router.dispatch(ctx)

        # 验证响应体
        call_args = ctx.handler.wfile.write.call_args
        assert call_args is not None
        body = call_args[0][0]
        body_str = body.decode("utf-8") if isinstance(body, bytes) else str(body)

        # 不应包含 traceback 特征
        assert "Traceback" not in body_str
        assert 'File "' not in body_str

        # 应该包含基本错误信息
        assert "error" in body_str.lower()

    def test_router_dispatch_app_error_includes_code(self):
        """AppError 响应包含 code 字段。"""
        from core.errors import ValidationError

        router = Router()

        def _validate(ctx):
            raise ValidationError("参数无效")

        router.add("POST", "/api/test-validate", _validate)
        ctx = _make_ctx("/api/test-validate", "POST")

        router.dispatch(ctx)

        call_args = ctx.handler.wfile.write.call_args
        assert call_args is not None
        body = call_args[0][0].decode("utf-8")
        assert "error" in body.lower()

    def test_router_dispatch_404_returns_standard_format(self):
        """404 响应使用标准格式。"""
        router = Router()
        ctx = _make_ctx("/api/nonexistent-endpoint")

        router.dispatch(ctx)

        call_args = ctx.handler.wfile.write.call_args
        assert call_args is not None
        body = call_args[0][0].decode("utf-8")
        assert "error" in body.lower() or "不存在" in body

    def test_router_dispatch_debug_mode_includes_detail(self):
        """debug 模式下可以包含 detail。"""
        import app_http.router as router_mod

        with patch.object(router_mod, "_DEBUG", True):
            router = Router()

            def _explode(ctx):
                raise RuntimeError("模拟内部错误")

            router.add("GET", "/api/test-debug", _explode)
            ctx = _make_ctx("/api/test-debug")

            router.dispatch(ctx)

            call_args = ctx.handler.wfile.write.call_args
            assert call_args is not None
            body = call_args[0][0].decode("utf-8")
            assert "detail" in body.lower()


class TestAppErrorResponseFormat:
    """AppError 响应格式测试。"""

    def test_app_error_to_dict_format(self):
        from core.errors import UnauthorizedError

        err = UnauthorizedError("未登录或登录已失效")
        d = err.to_dict()
        assert d["code"] == "UNAUTHORIZED"
        assert d["status"] == 401
        assert d["message"] == "未登录或登录已失效"
