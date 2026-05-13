"""入口点去重测试。

验证 app.py 不再复制完整服务实现。
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path


# 确保 backend/src 在 sys.path 中
_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


class TestEntrypointNoDuplicate:
    """app.py 和 main.py 不应重复实现。"""

    def test_app_py_no_build_router_definition(self):
        """app.py 不应包含自己的 build_router 定义。"""
        # 读取 app.py 源码（不 import，因为会触发副作用）
        app_path = _SRC / "app.py"
        source = app_path.read_text(encoding="utf-8")
        # 不应有 def build_router
        assert "def build_router" not in source, (
            "app.py 不应包含 build_router() 实现，应从 app_http.server 导入"
        )

    def test_app_py_no_api_handler_definition(self):
        """app.py 不应包含自己的 ApiHandler 定义。"""
        app_path = _SRC / "app.py"
        source = app_path.read_text(encoding="utf-8")
        assert "class ApiHandler" not in source, (
            "app.py 不应包含 ApiHandler 实现，应从 app_http.server 导入"
        )

    def test_app_py_no_run_server_definition(self):
        """app.py 不应包含自己的 run_server 定义。"""
        app_path = _SRC / "app.py"
        source = app_path.read_text(encoding="utf-8")
        assert "def run_server" not in source, (
            "app.py 不应包含 run_server() 实现，应从 app_http.server 导入"
        )

    def test_main_py_no_build_router_definition(self):
        """main.py 不应包含自己的 build_router 定义。"""
        main_path = _SRC / "main.py"
        source = main_path.read_text(encoding="utf-8")
        assert "def build_router" not in source, (
            "main.py 不应包含 build_router() 实现，应从 app_http.server 导入"
        )

    def test_main_py_no_api_handler_definition(self):
        """main.py 不应包含自己的 ApiHandler 定义。"""
        main_path = _SRC / "main.py"
        source = main_path.read_text(encoding="utf-8")
        assert "class ApiHandler" not in source, (
            "main.py 不应包含 ApiHandler 实现，应从 app_http.server 导入"
        )

    def test_main_py_imports_from_server(self):
        """main.py 应从 app_http.server 导入。"""
        main_path = _SRC / "main.py"
        source = main_path.read_text(encoding="utf-8")
        assert "from app_http.server import" in source, (
            "main.py 应从 app_http.server 导入共享实现"
        )

    def test_app_py_imports_from_server(self):
        """app.py 应从 app_http.server 导入。"""
        app_path = _SRC / "app.py"
        source = app_path.read_text(encoding="utf-8")
        assert "from app_http.server import" in source, (
            "app.py 应从 app_http.server 导入共享实现"
        )

    def test_build_router_exists_in_server(self):
        """app_http/server.py 包含 build_router 定义。"""
        server_path = _SRC / "app_http" / "server.py"
        source = server_path.read_text(encoding="utf-8")
        assert "def build_router" in source, (
            "app_http/server.py 应包含唯一的 build_router() 实现"
        )

    def test_api_handler_exists_in_server(self):
        """app_http/server.py 包含 ApiHandler 定义。"""
        server_path = _SRC / "app_http" / "server.py"
        source = server_path.read_text(encoding="utf-8")
        assert "class ApiHandler" in source, (
            "app_http/server.py 应包含唯一的 ApiHandler 实现"
        )

    def test_run_server_exists_in_server(self):
        """app_http/server.py 包含 run_server 定义。"""
        server_path = _SRC / "app_http" / "server.py"
        source = server_path.read_text(encoding="utf-8")
        assert "def run_server" in source, (
            "app_http/server.py 应包含唯一的 run_server() 实现"
        )
