"""数据库表管理和引导工具 —— 兼容导出入口。

本文件保留作为向后兼容的导出入口，实际实现已迁移到 database/ 包。
新代码请直接从 database/ 包导入。
"""

from __future__ import annotations

# ── 兼容导出：保持所有现有 import 路径有效 ──
from database.bootstrap import ensure_admin_tables  # noqa: F401
from database.summary import database_summary  # noqa: F401
from database.migrations import add_column_if_missing, ensure_column  # noqa: F401
from database.connection import default_db_target  # noqa: F401
from database.seed import seed_default_lottery_types  # noqa: F401
from database.schema.indexes import ensure_indexes  # noqa: F401
