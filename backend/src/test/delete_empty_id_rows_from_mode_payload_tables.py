"""删除 PostgreSQL `public.mode_payload_{x}` 表中 `id` 为空的记录。

用途：
1. 扫描 `public` schema 下所有 `mode_payload_数字` 表
2. 仅处理包含 `id` 列的表
3. 删除 `id IS NULL` 或 `CAST(id AS TEXT)` 为空字符串的记录
4. 输出每张表的命中数量、删除数量和最终汇总

示例：
    python backend/src/test/delete_empty_id_rows_from_mode_payload_tables.py
    python backend/src/test/delete_empty_id_rows_from_mode_payload_tables.py --dry-run
    python backend/src/test/delete_empty_id_rows_from_mode_payload_tables.py --db-path "postgresql://postgres:***@localhost:5432/liuhecai"
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = BACKEND_ROOT / "src"
TEST_ROOT = SRC_ROOT / "test"

for path_item in (TEST_ROOT, SRC_ROOT):
    if str(path_item) not in sys.path:
        sys.path.insert(0, str(path_item))

import config as app_config  # noqa: E402
from db import connect, detect_database_engine, quote_identifier  # noqa: E402


MODE_PAYLOAD_TABLE_RE = re.compile(r"^mode_payload_\d+$")
SCHEMA_NAME = "public"

_db_cfg = app_config.section("database")
DEFAULT_POSTGRES_DSN = str(
    _db_cfg.get("default_postgres_dsn", "postgresql://postgres:2225427@localhost:5432/liuhecai")
)


def default_db_target() -> str:
    """返回脚本默认使用的数据库目标。

    Args:
        无。

    Returns:
        str: 优先使用 `LOTTERY_DB_PATH`、`DATABASE_URL`，否则回退到
        `config.yaml` 中配置的本地 PostgreSQL DSN。
    """

    return (
        str(os.environ.get("LOTTERY_DB_PATH") or "").strip()
        or str(os.environ.get("DATABASE_URL") or "").strip()
        or DEFAULT_POSTGRES_DSN
    )


def validate_mode_payload_table_name(table_name: str) -> str:
    """校验表名是否为安全的 `mode_payload_{数字}` 格式。

    Args:
        table_name: 待校验的表名。

    Returns:
        str: 校验通过后的表名原值。

    Raises:
        ValueError: 当表名不符合 `mode_payload_{数字}` 格式时抛出。
    """

    normalized = str(table_name or "").strip()
    if not MODE_PAYLOAD_TABLE_RE.fullmatch(normalized):
        raise ValueError(f"无效的 mode_payload 表名: {table_name}")
    return normalized


def list_public_mode_payload_tables(db_path: str | Path) -> list[str]:
    """读取 `public` schema 下全部 `mode_payload_{x}` 表名。

    Args:
        db_path: 数据库目标 DSN。

    Returns:
        list[str]: 已按表名排序的目标表列表。
    """

    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = ?
              AND table_type = 'BASE TABLE'
              AND table_name LIKE ?
            ORDER BY table_name
            """,
            (SCHEMA_NAME, "mode_payload_%"),
        ).fetchall()

    tables: list[str] = []
    for row in rows:
        table_name = str(row["table_name"])
        if MODE_PAYLOAD_TABLE_RE.fullmatch(table_name):
            tables.append(table_name)
    return tables


def table_has_id_column(db_path: str | Path, table_name: str) -> bool:
    """判断目标表是否包含 `id` 列。

    Args:
        db_path: 数据库目标 DSN。
        table_name: 待检查的表名。

    Returns:
        bool: 包含 `id` 列返回 `True`，否则返回 `False`。
    """

    validate_mode_payload_table_name(table_name)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = ?
              AND table_name = ?
              AND column_name = 'id'
            """,
            (SCHEMA_NAME, table_name),
        ).fetchone()
    return bool(row)


def count_empty_id_rows(db_path: str | Path, table_name: str) -> int:
    """统计单张表中 `id` 为空的记录数量。

    判定规则：
    1. `id IS NULL`
    2. `BTRIM(CAST(id AS TEXT)) = ''`

    Args:
        db_path: 数据库目标 DSN。
        table_name: 目标表名。

    Returns:
        int: 符合“空 id”条件的记录数。
    """

    safe_table_name = validate_mode_payload_table_name(table_name)
    qualified_table_name = f"{quote_identifier(SCHEMA_NAME)}.{quote_identifier(safe_table_name)}"

    with connect(db_path) as conn:
        row = conn.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM {qualified_table_name}
            WHERE id IS NULL
               OR BTRIM(CAST(id AS TEXT)) = ''
            """
        ).fetchone()

    return int(row["total"] or 0) if row else 0


def delete_empty_id_rows(
    db_path: str | Path,
    table_name: str,
    dry_run: bool = False,
) -> int:
    """删除单张表中 `id` 为空的记录。

    Args:
        db_path: 数据库目标 DSN。
        table_name: 目标表名。
        dry_run: 是否仅预览不执行删除。`True` 时返回待删数量但不落库。

    Returns:
        int: 实际删除数量；若 `dry_run=True`，则返回待删除数量。
    """

    safe_table_name = validate_mode_payload_table_name(table_name)
    qualified_table_name = f"{quote_identifier(SCHEMA_NAME)}.{quote_identifier(safe_table_name)}"

    with connect(db_path) as conn:
        hit_count_row = conn.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM {qualified_table_name}
            WHERE id IS NULL
               OR BTRIM(CAST(id AS TEXT)) = ''
            """
        ).fetchone()
        hit_count = int(hit_count_row["total"] or 0) if hit_count_row else 0

        if dry_run or hit_count == 0:
            return hit_count

        cursor = conn.execute(
            f"""
            DELETE FROM {qualified_table_name}
            WHERE id IS NULL
               OR BTRIM(CAST(id AS TEXT)) = ''
            """
        )
        conn.commit()
        return max(int(cursor.rowcount), 0)


def cleanup_mode_payload_empty_ids(
    db_path: str | Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """批量清理所有 `public.mode_payload_{x}` 表中的空 `id` 记录。

    Args:
        db_path: 数据库目标 DSN。
        dry_run: 是否仅统计不执行删除。

    Returns:
        dict[str, Any]: 包含汇总结果和逐表明细的结果字典。

    Raises:
        ValueError: 当数据库目标不是 PostgreSQL 时抛出。
    """

    if detect_database_engine(db_path) != "postgres":
        raise ValueError("该脚本仅支持 PostgreSQL 数据库目标。")

    tables = list_public_mode_payload_tables(db_path)
    details: list[dict[str, Any]] = []
    total_hits = 0
    total_deleted = 0

    for table_name in tables:
        if not table_has_id_column(db_path, table_name):
            details.append(
                {
                    "table_name": table_name,
                    "has_id_column": False,
                    "matched_rows": 0,
                    "deleted_rows": 0,
                }
            )
            print(f"[跳过] {SCHEMA_NAME}.{table_name}: 不存在 id 列")
            continue

        matched_rows = count_empty_id_rows(db_path, table_name)
        deleted_rows = delete_empty_id_rows(db_path, table_name, dry_run=dry_run)
        total_hits += matched_rows
        total_deleted += deleted_rows

        details.append(
            {
                "table_name": table_name,
                "has_id_column": True,
                "matched_rows": matched_rows,
                "deleted_rows": deleted_rows,
            }
        )

        action_label = "待删除" if dry_run else "已删除"
        print(
            f"[完成] {SCHEMA_NAME}.{table_name}: "
            f"命中 {matched_rows} 行，{action_label} {deleted_rows} 行"
        )

    return {
        "db_path": str(db_path),
        "schema": SCHEMA_NAME,
        "dry_run": dry_run,
        "table_count": len(tables),
        "matched_rows": total_hits,
        "deleted_rows": total_deleted,
        "details": details,
    }


def print_summary(result: dict[str, Any]) -> None:
    """打印清理结果汇总。

    Args:
        result: `cleanup_mode_payload_empty_ids()` 返回的结果字典。

    Returns:
        None: 仅输出汇总信息到控制台。
    """

    print("-" * 72)
    print("清理完成")
    print(f"数据库: {result['db_path']}")
    print(f"Schema: {result['schema']}")
    print(f"模式: {'仅预览' if result['dry_run'] else '实际删除'}")
    print(f"扫描表数量: {result['table_count']}")
    print(f"命中空 id 行数: {result['matched_rows']}")
    print(f"删除空 id 行数: {result['deleted_rows']}")
    print("-" * 72)


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。

    Args:
        无。

    Returns:
        argparse.ArgumentParser: 配置好的解析器对象。
    """

    parser = argparse.ArgumentParser(
        description="删除 PostgreSQL public.mode_payload_{x} 表中 id 为空的记录。"
    )
    parser.add_argument(
        "--db-path",
        default=default_db_target(),
        help="数据库目标，必须是 PostgreSQL DSN；默认读取本地项目 PostgreSQL 配置。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="仅统计待删除数量，不执行实际删除。",
    )
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    summary = cleanup_mode_payload_empty_ids(
        db_path=args.db_path,
        dry_run=bool(args.dry_run),
    )
    print_summary(summary)
