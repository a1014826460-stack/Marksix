"""routes/common.py 兼容性测试。

验证 routes/common.py 中的后台任务函数来自统一实现（jobs/handlers）。
"""

from __future__ import annotations

import sys
from pathlib import Path


# 确保 backend/src 在 sys.path 中
_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


class TestRoutesCommonCompat:
    """routes/common.py 不应重复实现，应从 jobs/handlers 导入。"""

    def test_create_fetch_run_imported_not_defined(self):
        """create_fetch_run 应从 jobs/handlers 导入，不自己定义。"""
        common_path = _SRC / "routes" / "common.py"
        source = common_path.read_text(encoding="utf-8")
        # 应该从 jobs.handlers 导入，而不是自己定义
        assert "from jobs.handlers import" in source, (
            "routes/common.py 应从 jobs/handlers 导入后台任务函数"
        )
        # 不应该有 def create_fetch_run（除了可能的注释）
        lines_with_def = [l for l in source.split("\n") if "def create_fetch_run" in l]
        assert len(lines_with_def) == 0, (
            f"routes/common.py 不应定义 create_fetch_run，应从 jobs/handlers 导入。"
            f" 发现: {lines_with_def}"
        )

    def test_finish_fetch_run_imported_not_defined(self):
        """finish_fetch_run 应从 jobs/handlers 导入，不自己定义。"""
        common_path = _SRC / "routes" / "common.py"
        source = common_path.read_text(encoding="utf-8")
        lines_with_def = [l for l in source.split("\n") if "def finish_fetch_run" in l]
        assert len(lines_with_def) == 0, (
            f"routes/common.py 不应定义 finish_fetch_run，应从 jobs/handlers 导入。"
            f" 发现: {lines_with_def}"
        )

    def test_list_fetch_runs_imported_not_defined(self):
        """list_fetch_runs 应从 jobs/handlers 导入，不自己定义。"""
        common_path = _SRC / "routes" / "common.py"
        source = common_path.read_text(encoding="utf-8")
        lines_with_def = [l for l in source.split("\n") if "def list_fetch_runs" in l]
        assert len(lines_with_def) == 0, (
            f"routes/common.py 不应定义 list_fetch_runs，应从 jobs/handlers 导入。"
            f" 发现: {lines_with_def}"
        )

    def test_start_background_job_imported_not_defined(self):
        """start_background_job 应从 jobs/handlers 导入，不自己定义。"""
        common_path = _SRC / "routes" / "common.py"
        source = common_path.read_text(encoding="utf-8")
        lines_with_def = [l for l in source.split("\n") if "def start_background_job" in l]
        assert len(lines_with_def) == 0, (
            f"routes/common.py 不应定义 start_background_job，应从 jobs/handlers 导入。"
            f" 发现: {lines_with_def}"
        )

    def test_crawl_and_generate_is_thin_wrapper(self):
        """crawl_and_generate 应为薄包装，委托给 crawler_service。"""
        common_path = _SRC / "routes" / "common.py"
        source = common_path.read_text(encoding="utf-8")
        assert "crawl_and_generate_for_type" in source, (
            "crawl_and_generate 应委托给 crawler_service.crawl_and_generate_for_type"
        )

    def test_jobs_handlers_has_required_functions(self):
        """jobs/handlers.py 应包含核心函数定义。"""
        handlers_path = _SRC / "jobs" / "handlers.py"
        source = handlers_path.read_text(encoding="utf-8")
        assert "def start_background_job" in source
        assert "def get_background_job" in source
        assert "def create_fetch_run" in source
        assert "def finish_fetch_run" in source
        assert "def list_fetch_runs" in source

    def test_routes_common_exports_required_functions(self):
        """routes/common.py 应导出所有必需的后台任务函数。"""
        # 通过源码分析验证 import
        common_path = _SRC / "routes" / "common.py"
        source = common_path.read_text(encoding="utf-8")
        for func in ("start_background_job", "get_background_job",
                      "create_fetch_run", "finish_fetch_run", "list_fetch_runs"):
            # 应该在导入列表中
            assert func in source, (
                f"routes/common.py 应导出 {func}"
            )


class TestRoutesCommonThinWrapper:
    """验证薄包装函数委托给正确实现。"""

    def test_crawl_and_generate_delegates_to_crawler_service(self):
        """crawl_and_generate 委托给 crawl_and_generate_for_type。"""
        from routes.common import crawl_and_generate as _cg

        # 检查函数源码
        source = _cg.__code__.co_names
        assert "crawl_and_generate_for_type" in source, (
            "crawl_and_generate 应直接委托给 crawl_and_generate_for_type"
        )

    def test_fetch_site_data_uses_imported_create_fetch_run(self):
        """fetch_site_data 应使用从 jobs/handlers 导入的 create_fetch_run。"""
        from routes.common import fetch_site_data as _fsd

        # fetch_site_data 的实现应引用导入的 create_fetch_run
        source = _fsd.__code__.co_names
        assert "create_fetch_run" in source
