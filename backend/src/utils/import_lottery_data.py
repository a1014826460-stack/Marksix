"""从 backend/lottery_data 目录导入 JSON 文件到 PostgreSQL 的 mode_payload_* 表。

用法:
    python backend/src/utils/import_lottery_data.py
    python backend/src/utils/import_lottery_data.py --db-target "postgresql://user:pass@host:5432/db"
    python backend/src/utils/import_lottery_data.py --data-dir "path/to/lottery_data"
    python backend/src/utils/import_lottery_data.py --skip-web-migration
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = BACKEND_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import config as app_config
from db import connect, quote_identifier

_db_cfg = app_config.load_config().get("database", {})
DEFAULT_POSTGRES_DSN = str(
    _db_cfg.get(
        "default_postgres_dsn",
        "postgresql://postgres:2225427@localhost:5432/liuhecai",
    )
)
DEFAULT_DATA_DIR = BACKEND_ROOT / "lottery_data"
TABLE_PREFIX = "mode_payload_"

FILENAME_PATTERN = re.compile(
    r"lottery_web(\d+)_mode(\d+)_(\d{8})_(\d{6})\.json"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("import_lottery_data")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def normalize_column_name(key: str) -> str:
    col = re.sub(r"\W+", "_", key.strip(), flags=re.ASCII).strip("_").lower()
    if not col:
        return "value"
    if col[0].isdigit():
        col = f"field_{col}"
    return col


def infer_sql_type(values: list[Any]) -> str:
    """根据一批值推断最合适的 SQL 列类型。"""
    non_empty = [v for v in values if v is not None and v != ""]
    if not non_empty:
        return "TEXT"
    if all(isinstance(v, bool) for v in non_empty):
        return "INTEGER"
    if all(isinstance(v, int) and not isinstance(v, bool) for v in non_empty):
        return "INTEGER"
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in non_empty):
        return "REAL"
    return "TEXT"


def payload_value_to_sql(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return int(value)
    return value


def parse_mode_id(filename: str) -> int | None:
    """从文件名提取 mode_id。"""
    basename = Path(filename).name
    match = FILENAME_PATTERN.search(basename)
    if match:
        return int(match.group(2))
    return None


# ---------------------------------------------------------------------------
# table management
# ---------------------------------------------------------------------------

def ensure_mode_payload_table(conn: Any, mode_id: int, sample_row: dict[str, Any]) -> str:
    """确保目标表存在且包含所需列和 id 唯一约束，返回表名。"""
    table_name = f"{TABLE_PREFIX}{mode_id}"
    quoted_table = quote_identifier(table_name)

    column_map = {key: normalize_column_name(key) for key in sample_row.keys()}

    if conn.table_exists(table_name):
        existing_cols = set(conn.table_columns(table_name))
        for key, col_name in column_map.items():
            if col_name not in existing_cols:
                sample_values = [sample_row.get(key)]
                sql_type = infer_sql_type(sample_values)
                logger.info("  添加列 %s.%s %s", table_name, col_name, sql_type)
                conn.execute(
                    f"ALTER TABLE {quoted_table} "
                    f"ADD COLUMN {quote_identifier(col_name)} {sql_type}"
                )

        # 尝试为 id 列建立唯一索引（如果尚不存在），以便 ON CONFLICT 能正常工作
        _ensure_id_unique_index(conn, table_name)
        return table_name

    # 创建新表：以 id 为主键
    column_defs: list[str] = []
    for key, col_name in column_map.items():
        values = [sample_row.get(key)]
        sql_type = infer_sql_type(values)
        column_defs.append(f"{quote_identifier(col_name)} {sql_type}")

    id_col = column_map.get("id", "id")
    column_defs.append(f"PRIMARY KEY ({quote_identifier(id_col)})")

    create_sql = f"CREATE TABLE {quoted_table} ({', '.join(column_defs)})"
    conn.execute(create_sql)
    logger.info("  创建表 %s (%d 列)", table_name, len(column_defs))
    return table_name


def _ensure_id_unique_index(conn: Any, table_name: str) -> None:
    """为已有表添加 id 列唯一索引（如果不存在），忽略重复数据导致的失败。"""
    quoted_table = quote_identifier(table_name)
    index_name = f"idx_{table_name}_id_unique"

    # 检查是否已有主键或唯一约束覆盖 id 列
    existing_pk = conn.execute(
        """
        SELECT 1
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.table_schema = current_schema()
          AND tc.table_name = %s
          AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
          AND kcu.column_name = 'id'
        LIMIT 1
        """,
        (table_name,),
    ).fetchone()

    if existing_pk:
        return

    try:
        conn.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {quote_identifier(index_name)} "
            f"ON {quoted_table} (id)"
        )
    except Exception as exc:
        logger.warning("  无法为 %s 创建 id 唯一索引（可能存在重复数据）: %s", table_name, exc)


# ---------------------------------------------------------------------------
# data import
# ---------------------------------------------------------------------------

def upsert_records(
    conn: Any,
    table_name: str,
    records: list[dict[str, Any]],
    column_map: dict[str, str],
) -> int:
    """逐条 UPSERT 记录，返回成功写入的记录数。"""
    quoted_table = quote_identifier(table_name)
    col_names = [column_map[k] for k in column_map]
    quoted_cols = ", ".join(quote_identifier(c) for c in col_names)
    placeholders = ", ".join(["%s"] * len(col_names))
    update_set = ", ".join(
        f"{quote_identifier(c)} = EXCLUDED.{quote_identifier(c)}" for c in col_names
    )

    sql = (
        f"INSERT INTO {quoted_table} ({quoted_cols}) "
        f"VALUES ({placeholders}) "
        f"ON CONFLICT (id) DO UPDATE SET {update_set}"
    )

    success = 0
    failed = 0

    for idx, record in enumerate(records):
        try:
            values = tuple(
                payload_value_to_sql(record.get(key)) for key in column_map
            )
            conn.execute(sql, values)
            success += 1
        except Exception:
            # 回退：先删后插（适用于 id 列没有唯一约束的旧表）
            try:
                rid = record.get("id")
                if rid is not None:
                    conn.execute(
                        f"DELETE FROM {quoted_table} WHERE id = %s", (rid,)
                    )
                cols_only = ", ".join(
                    quote_identifier(column_map[k]) for k in column_map
                )
                vals_only = ", ".join(["%s"] * len(column_map))
                conn.execute(
                    f"INSERT INTO {quoted_table} ({cols_only}) VALUES ({vals_only})",
                    tuple(
                        payload_value_to_sql(record.get(key))
                        for key in column_map
                    ),
                )
                success += 1
            except Exception as fallback_err:
                logger.error(
                    "  跳过记录 id=%s: %s", record.get("id"), fallback_err
                )
                failed += 1
                continue

        if (idx + 1) % 200 == 0:
            logger.info("  已处理 %d/%d 条...", idx + 1, len(records))

    if failed:
        logger.warning("  %d 条记录导入失败", failed)
    return success


def build_column_map(records: list[dict[str, Any]]) -> dict[str, str]:
    """为一批记录构建统一的 JSON key → 列名映射。"""
    column_map: dict[str, str] = {}
    used: set[str] = set()
    for record in records:
        for key in record:
            if key in column_map:
                continue
            col = normalize_column_name(key)
            candidate = col
            idx = 2
            while candidate in used:
                candidate = f"{col}_{idx}"
                idx += 1
            column_map[key] = candidate
            used.add(candidate)
    return column_map


def import_json_file(conn: Any, filepath: Path) -> tuple[int, int, int]:
    """导入单个 JSON 文件，返回 (mode_id, total, errors)。"""
    filename = filepath.name

    mode_id = parse_mode_id(filename)
    if mode_id is None:
        with open(filepath, "r", encoding="utf-8") as fh:
            meta = json.load(fh)
        mode_id = meta.get("modes_id")
        if mode_id is None:
            logger.error("  无法从文件名或 JSON 内容解析 mode_id，跳过: %s", filename)
            return 0, 0, 1

    logger.info("处理 %s → mode_payload_%d", filename, mode_id)

    with open(filepath, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    records: list[dict[str, Any]] = data.get("data", [])
    if not records:
        logger.warning("  文件中无 data 记录，跳过: %s", filename)
        return mode_id, 0, 0

    column_map = build_column_map(records)
    table_name = ensure_mode_payload_table(conn, mode_id, records[1])

    success = upsert_records(conn, table_name, records, column_map)

    logger.info(
        "  mode_payload_%d: 成功导入 %d/%d 条记录",
        mode_id,
        success,
        len(records),
    )
    return mode_id, success, 0


# ---------------------------------------------------------------------------
# web migration: web=2 → web=4
# ---------------------------------------------------------------------------

def migrate_web2_to_web4(conn: Any, mode_ids: set[int]) -> None:
    """将各 mode_payload 表中 web=2 的记录更新为 web=4，按 year+term+res_code 处理冲突。"""
    logger.info("开始 web=2 → web=4 数据修正...")
    total_migrated = 0

    for mode_id in sorted(mode_ids):
        table_name = f"{TABLE_PREFIX}{mode_id}"
        quoted_table = quote_identifier(table_name)

        if not conn.table_exists(table_name):
            continue

        columns = conn.table_columns(table_name)
        web_col = "web" if "web" in columns else ("web_id" if "web_id" in columns else None)
        if web_col is None:
            continue

        quoted_web = quote_identifier(web_col)
        # 使用 CAST 避免 TEXT / INTEGER 类型不匹配
        web_col_cast = f"CAST({quoted_web} AS text)"
        match_cols = ("year", "term", "res_code")
        if any(col not in columns for col in match_cols):
            logger.warning(
                "  mode_payload_%d: 缺少 year/term/res_code 列，跳过 web=2→4 修正",
                mode_id,
            )
            continue

        def cast_text_expr(alias: str, col_name: str) -> str:
            return f"CAST({alias}.{quote_identifier(col_name)} AS text)"

        match_condition = " AND ".join(
            f"{cast_text_expr('src', col)} IS NOT DISTINCT FROM {cast_text_expr('dst', col)}"
            for col in match_cols
        )

        # 统计 web=2 记录数
        cnt_row = conn.execute(
            f"SELECT COUNT(*) AS cnt FROM {quoted_table} WHERE {web_col_cast} = '2'"
        ).fetchone()
        web2_count = int(cnt_row["cnt"] or 0) if cnt_row else 0
        if web2_count == 0:
            continue

        deleted_count = 0

        # 步骤 1：如果 web=4 已存在同一条 mode 记录，则删除重复的 web=2 记录
        try:
            deleted = conn.execute(
                f"""
                DELETE FROM {quoted_table} AS src
                WHERE CAST(src.{quoted_web} AS text) = '2'
                  AND EXISTS (
                      SELECT 1
                      FROM {quoted_table} AS dst
                      WHERE CAST(dst.{quoted_web} AS text) = '4'
                        AND {match_condition}
                  )
                """
            )
            deleted_count = int(deleted.rowcount) if deleted.rowcount >= 0 else 0
            if deleted_count:
                logger.info(
                    "  mode_payload_%d: 删除 %d 条已存在于 web=4 的重复 web=2 记录",
                    mode_id,
                    deleted_count,
                )
        except Exception as exc:
            logger.warning(
                "  mode_payload_%d: 批量删除冲突记录失败，逐条处理: %s", mode_id, exc
            )
            web4_rows = conn.execute(
                f"""
                SELECT
                    {quote_identifier('year')} AS year,
                    {quote_identifier('term')} AS term,
                    {quote_identifier('res_code')} AS res_code
                FROM {quoted_table}
                WHERE {web_col_cast} = '4'
                """
            ).fetchall()
            deleted_count = 0
            for row in web4_rows:
                try:
                    result = conn.execute(
                        f"""
                        DELETE FROM {quoted_table}
                        WHERE {web_col_cast} = '2'
                          AND CAST({quote_identifier('year')} AS text) IS NOT DISTINCT FROM CAST(%s AS text)
                          AND CAST({quote_identifier('term')} AS text) IS NOT DISTINCT FROM CAST(%s AS text)
                          AND CAST({quote_identifier('res_code')} AS text) IS NOT DISTINCT FROM CAST(%s AS text)
                        """,
                        (row["year"], row["term"], row["res_code"]),
                    )
                    deleted_count += int(result.rowcount) if result.rowcount >= 0 else 0
                except Exception:
                    pass

        # 步骤 2：仅将仍未在 web=4 中存在的 web=2 记录并入 web=4
        try:
            result = conn.execute(
                f"UPDATE {quoted_table} SET {quoted_web} = '4' WHERE {web_col_cast} = '2'"
            )
            updated_count = int(result.rowcount) if result.rowcount >= 0 else 0
        except Exception as exc:
            logger.error("  mode_payload_%d: web=2→4 更新失败: %s", mode_id, exc)
            continue

        total_migrated += updated_count
        logger.info(
            "  mode_payload_%d: 补齐 %d 条到 web=4，删除重复 web=2 %d 条",
            mode_id,
            updated_count,
            deleted_count,
        )

    logger.info("web 迁移完成，共迁移 %d 条记录", total_migrated)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="从 JSON 文件导入数据到 PostgreSQL mode_payload_* 表"
    )
    parser.add_argument(
        "--db-target",
        default=None,
        help=f"PostgreSQL 连接串（默认使用 config.yaml 配置: {DEFAULT_POSTGRES_DSN}）",
    )
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help="包含 JSON 文件的目录路径",
    )
    parser.add_argument(
        "--skip-web-migration",
        action="store_true",
        help="跳过 web=2→4 的数据修正步骤",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅扫描文件，不执行数据库写入",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.is_dir():
        logger.error("数据目录不存在: %s", data_dir)
        sys.exit(1)

    db_target = args.db_target or DEFAULT_POSTGRES_DSN

    json_files = sorted(data_dir.glob("*.json"))
    if not json_files:
        logger.error("目录中无 JSON 文件: %s", data_dir)
        sys.exit(1)

    logger.info("找到 %d 个 JSON 文件", len(json_files))
    logger.info("数据库目标: %s", db_target)

    if args.dry_run:
        logger.info("=== DRY RUN 模式，仅列出文件 ===")
        for f in json_files:
            mid = parse_mode_id(f.name)
            logger.info("  %s → mode_payload_%s", f.name, mid or "?")
        return

    processed_mode_ids: set[int] = set()
    total_files = 0
    total_records = 0
    error_files = 0

    with connect(db_target) as conn:
        if conn.engine != "postgres":
            logger.error(
                "此脚本仅支持 PostgreSQL。当前数据库引擎: %s", conn.engine
            )
            sys.exit(1)

        for filepath in json_files:
            try:
                mode_id, count, errors = import_json_file(conn, filepath)
                if mode_id:
                    processed_mode_ids.add(mode_id)
                    total_records += count
                error_files += errors
                total_files += 1
            except Exception as exc:
                logger.error("导入文件失败 %s: %s", filepath.name, exc)
                error_files += 1
                continue

        if not args.skip_web_migration and processed_mode_ids:
            migrate_web2_to_web4(conn, processed_mode_ids)

    logger.info(
        "=== 导入完成: %d/%d 文件成功, 共 %d 条记录, %d 个表 ===",
        total_files - error_files,
        total_files,
        total_records,
        len(processed_mode_ids),
    )


if __name__ == "__main__":
    main()
