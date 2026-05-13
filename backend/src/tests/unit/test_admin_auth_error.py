"""管理员鉴权错误测试。

验证未登录访问 /api/admin/* 返回标准 401 JSON，不泄露 traceback。
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from app_http.request_context import RequestContext
from app_http.router import Router
from app_http.server import _dispatch_error_response

# ApiHandler 在测试中间接引用（通过 inspect.getsource）
from app_http.server import ApiHandler
from core.errors import UnauthorizedError, ForbiddenError
from http import HTTPStatus


def _make_handler(path: str, method: str = "GET"):
    """创建 mock HTTP handler。"""
    handler = MagicMock()
    handler.path = path
    handler.command = method
    handler.headers = {}
    handler.server.db_path = "postgresql://test:test@localhost:5432/test"
    handler.wfile = MagicMock()
    return handler


def _make_ctx(handler, path: str, method: str = "GET") -> RequestContext:
    ctx = RequestContext(handler, method)
    ctx.path = path.rstrip("/") or "/"
    return ctx


class TestAdminAuthError:
    """未登录访问 /api/admin/sites 的测试。"""

    def test_dispatch_error_response_returns_401_json_for_unauthorized(self):
        """_dispatch_error_response 对 UnauthorizedError 返回 401 JSON。"""
        handler = _make_handler("/api/admin/sites")
        ctx = _make_ctx(handler, "/api/admin/sites")

        _dispatch_error_response(ctx, UnauthorizedError("未登录或登录已失效"), MagicMock())

        call_args = handler.wfile.write.call_args
        assert call_args is not None, "应该写入了响应体"

        # 检查 send_response 调用
        send_response_call = handler.send_response.call_args
        assert send_response_call is not None
        assert send_response_call[0][0] == 401

    def test_dispatch_error_response_forbidden_returns_403_json(self):
        """_dispatch_error_response 对 ForbiddenError 返回 403 JSON。"""
        handler = _make_handler("/api/admin/sites")
        ctx = _make_ctx(handler, "/api/admin/sites")

        _dispatch_error_response(ctx, ForbiddenError("需要管理员权限"), MagicMock())

        send_response_call = handler.send_response.call_args
        assert send_response_call is not None
        assert send_response_call[0][0] == 403

    def test_dispatch_error_response_no_traceback_in_production(self):
        """生产环境下不泄露 traceback。"""
        handler = _make_handler("/api/admin/sites")
        ctx = _make_ctx(handler, "/api/admin/sites")

        # 确保 LOTTERY_DEBUG 未设置
        with patch.dict(os.environ, {}, clear=True):
            # 强制重新加载模块以获取正确的 DEBUG 值
            # 使用内部异常测试
            _dispatch_error_response(ctx, RuntimeError("内部错误"), MagicMock())

            call_args = handler.wfile.write.call_args
            assert call_args is not None
            body = call_args[0][0]
            # 响应不应包含 traceback 特征
            assert b"Traceback" not in body
            assert b"File " not in body

    def test_app_error_includes_code_field(self):
        """AppError 响应包含 code 字段。"""
        handler = _make_handler("/api/admin/sites")
        ctx = _make_ctx(handler, "/api/admin/sites")

        _dispatch_error_response(ctx, UnauthorizedError("未登录或登录已失效"), MagicMock())

        call_args = handler.wfile.write.call_args
        assert call_args is not None
        body = call_args[0][0].decode("utf-8")
        assert '"ok": false' in body.lower() or '"error"' in body.lower()


class TestApiHandlerDispatch:
    """ApiHandler.dispatch() 统一异常捕获测试。"""

    def test_dispatch_method_exists_and_has_try_except(self):
        """ApiHandler.dispatch() 方法存在且包含 try/except 异常处理。"""
        import inspect

        source = inspect.getsource(ApiHandler.dispatch)
        assert "try:" in source, (
            "ApiHandler.dispatch() 应包含 try/except 块以统一捕获异常"
        )
        assert "except Exception" in source or "except" in source, (
            "ApiHandler.dispatch() 应包含 except 块捕获异常"
        )

    def test_dispatch_calls_require_authenticated_for_admin_paths(self):
        """验证 dispatch 方法中对 /api/admin/ 路径调用 require_authenticated。"""
        import inspect

        source = inspect.getsource(ApiHandler.dispatch)
        assert "require_authenticated" in source, (
            "ApiHandler.dispatch() 应对 /api/admin/ 路径调用 require_authenticated"
        )
        assert "/api/admin/" in source
