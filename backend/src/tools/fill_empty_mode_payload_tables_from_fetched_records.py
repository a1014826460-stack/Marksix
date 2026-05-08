"""回填 PostgreSQL `public.mode_payload_{x}` 空表数据。

用途：
1. 扫描 `public` schema 下所有 `mode_payload_{数字}` 表
2. 找出“表存在且当前无任何记录”的目标表
3. 从 `public.fetched_mode_records` 中提取对应 `modes_id` 的历史记录
4. 将 `payload_json` 展开为列：JSON 的 key 作为列名，value 作为列值
5. 若目标表缺失某些列，则先自动补列，再执行批量插入

注意：
1. 该脚本只处理“已存在但为空”的 `mode_payload_{x}` 表
2. `payload_json` 中的对象/数组会转成 JSON 字符串后写入
3. 除 `payload_json` 字段外，还会补写 `web_id`、`modes_id`、`source_record_id`、`fetched_at`
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = BACKEND_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import config as app_config  # noqa: E402
from db import connect, detect_database_engine, quote_identifier  # noqa: E402


SCHEMA_NAME = "public"
FETCHED_RECORDS_TABLE = "fetched_mode_records"
MODE_PAYLOAD_TABLE_RE = re.compile(r"^mode_payload_(\d+)$")
RESERVED_COLUMN_FALLBACK = "value"

_db_cfg = app_config.section("database")
DEFAULT_POSTGRES_DSN = str(
    _db_cfg.get("default_postgres_dsn", "postgresql://postgres:2225427@localhost:5432/liuhecai")
)


def default_db_target() -> str:
    """返回脚本默认使用的数据库目标。

    Args:
        无。

    Returns:
        str: 优先读取 `LOTTERY_DB_PATH`、`DATABASE_URL`，否则回退到本地 PostgreSQL DSN。
    """

    return (
        str(os.environ.get("LOTTERY_DB_PATH") or "").strip()
        or str(os.environ.get("DATABASE_URL") or "").strip()
        or DEFAULT_POSTGRES_DSN
    )


def quote_qualified_table(schema_name: str, table_name: str) -> str:
    """拼接带 schema 的安全表名。

    Args:
        schema_name: schema 名称。
        table_name: 表名称。

    Returns:
        str: 形如 `"public"."mode_payload_53"` 的安全 SQL 片段。
    """

    return f"{quote_identifier(schema_name)}.{quote_identifier(table_name)}"


def validate_mode_payload_table_name(table_name: str) -> tuple[str, int]:
    """校验 `mode_payload_{数字}` 表名并提取 `modes_id`。

    Args:
        table_name: 待校验的表名。

    Returns:
        tuple[str, int]: 规范化后的表名与解析出的 `modes_id`。

    Raises:
        ValueError: 当表名不符合 `mode_payload_{数字}` 格式时抛出。
    """

    normalized = str(table_name or "").strip()
    match = MODE_PAYLOAD_TABLE_RE.fullmatch(normalized)
    if not match:
        raise ValueError(f"无效的 mode_payload 表名: {table_name}")
    return normalized, int(match.group(1))


def normalize_column_name(key: str) -> str:
    """将 `payload_json` 的 key 归一化为合法列名。

    Args:
        key: `payload_json` 中的原始 key。

    Returns:
        str: 归一化后的列名，仅包含小写字母、数字与下划线。
    """

    raw_text = str(key or "").strip()
    normalized = re.sub(r"[^0-9a-zA-Z_]+", "_", raw_text).strip("_").lower()
    if not normalized:
        normalized = RESERVED_COLUMN_FALLBACK
    if normalized[0].isdigit():
        normalized = f"field_{normalized}"
    return normalized


def payload_value_to_sql(value: Any) -> Any:
    """将 `payload_json` 的值转换为可落库的标量。

    Args:
        value: 原始 JSON 值。

    Returns:
        Any: 可直接插入数据库的值。对象/数组会被转成 JSON 字符串。
    """

    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return int(value)
    return value


def infer_sql_type(values: list[Any]) -> str:
    """根据样本值推断新增列类型。

    Args:
        values: 同一列的样本值列表。

    Returns:
        str: PostgreSQL 列类型，当前只会返回 `INTEGER`、`REAL` 或 `TEXT`。
    """

    non_empty_values = [value for value in values if value not in (None, "")]
    if not non_empty_values:
        return "TEXT"

    if all(isinstance(value, bool) for value in non_empty_values):
        return "INTEGER"

    if all(isinstance(value, int) and not isinstance(value, bool) for value in non_empty_values):
        return "INTEGER"

    if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in non_empty_values):
        return "REAL"

    return "TEXT"


def list_public_mode_payload_tables(db_path: str | Path) -> list[str]:
    """列出 `public` schema 下全部 `mode_payload_{x}` 表。

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


def count_table_rows(db_path: str | Path, table_name: str) -> int:
    """统计目标表的当前记录数。

    Args:
        db_path: 数据库目标 DSN。
        table_name: 目标表名。

    Returns:
        int: 表中的记录总数。
    """

    safe_table_name, _ = validate_mode_payload_table_name(table_name)
    qualified_table_name = quote_qualified_table(SCHEMA_NAME, safe_table_name)
    with connect(db_path) as conn:
        row = conn.execute(f"SELECT COUNT(*) AS total FROM {qualified_table_name}").fetchone()
    return int(row["total"] or 0) if row else 0


def load_fetched_mode_records(db_path: str | Path, modes_id: int) -> list[dict[str, Any]]:
    """读取指定 `modes_id` 的抓取历史记录。

    Args:
        db_path: 数据库目标 DSN。
        modes_id: 需要提取的玩法 ID。

    Returns:
        list[dict[str, Any]]: 已按时间与来源排序的原始抓取记录列表。
    """

    with connect(db_path) as conn:
        if not conn.table_exists(FETCHED_RECORDS_TABLE):
            raise ValueError("数据库中不存在 fetched_mode_records 表")

        rows = conn.execute(
            f"""
            SELECT web_id, modes_id, source_record_id, year, term, fetched_at, payload_json
            FROM {quote_identifier(FETCHED_RECORDS_TABLE)}
            WHERE modes_id = ?
            ORDER BY
                CAST(COALESCE(NULLIF(CAST(year AS TEXT), ''), '0') AS INTEGER),
                CAST(COALESCE(NULLIF(CAST(term AS TEXT), ''), '0') AS INTEGER),
                CAST(COALESCE(NULLIF(CAST(source_record_id AS TEXT), ''), '0') AS INTEGER)
            """,
            (modes_id,),
        ).fetchall()

    result: list[dict[str, Any]] = []
    for row in rows:
        payload = json.loads(str(row["payload_json"] or "{}"))
        result.append(
            {
                "web_id": row["web_id"],
                "modes_id": row["modes_id"],
                "source_record_id": row["source_record_id"],
                "year": row["year"],
                "term": row["term"],
                "fetched_at": row["fetched_at"],
                "payload": payload if isinstance(payload, dict) else {},
            }
        )
    return result


def build_insert_rows(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, list[Any]]]:
    """将 `fetched_mode_records` 记录转换为待插入行数据。

    Args:
        records: `load_fetched_mode_records()` 读取出的原始抓取记录。

    Returns:
        tuple[list[dict[str, Any]], dict[str, list[Any]]]:
            第一个值是标准化后的待插入行列表，
            第二个值是“列名 -> 样本值列表”的映射，用于推断新增列类型。
    """

    insert_rows: list[dict[str, Any]] = []
    column_samples: dict[str, list[Any]] = {}

    for record in records:
        row_data: dict[str, Any] = {
            "web_id": record["web_id"],
            "modes_id": record["modes_id"],
            "source_record_id": record["source_record_id"],
            "fetched_at": record["fetched_at"],
        }

        payload = record.get("payload") or {}
        for raw_key, raw_value in payload.items():
            column_name = normalize_column_name(str(raw_key))
            sql_value = payload_value_to_sql(raw_value)
            row_data[column_name] = sql_value
            column_samples.setdefault(column_name, []).append(sql_value)

        for meta_key in ("web_id", "modes_id", "source_record_id", "fetched_at"):
            column_samples.setdefault(meta_key, []).append(row_data.get(meta_key))

        insert_rows.append(row_data)

    return insert_rows, column_samples


def ensure_table_columns(
    db_path: str | Path,
    table_name: str,
    column_samples: dict[str, list[Any]],
) -> list[str]:
    """确保目标表具备插入所需的全部列。

    Args:
        db_path: 数据库目标 DSN。
        table_name: 目标 `mode_payload_{x}` 表名。
        column_samples: “列名 -> 样本值列表”的映射，用于判断要补哪些列以及列类型。

    Returns:
        list[str]: 本次新增的列名列表。
    """

    safe_table_name, _ = validate_mode_payload_table_name(table_name)
    qualified_table_name = quote_qualified_table(SCHEMA_NAME, safe_table_name)

    with connect(db_path) as conn:
        existing_columns = set(conn.table_columns(safe_table_name))
        added_columns: list[str] = []

        for column_name, samples in sorted(column_samples.items(), key=lambda item: item[0]):
            if column_name in existing_columns:
                continue
            sql_type = infer_sql_type(samples)
            conn.execute(
                f"""
                ALTER TABLE {qualified_table_name}
                ADD COLUMN {quote_identifier(column_name)} {sql_type}
                """
            )
            added_columns.append(column_name)

        conn.commit()
    return added_columns


def bulk_insert_rows(
    db_path: str | Path,
    table_name: str,
    rows: list[dict[str, Any]],
) -> int:
    """批量插入标准化后的行数据。

    Args:
        db_path: 数据库目标 DSN。
        table_name: 目标 `mode_payload_{x}` 表名。
        rows: 待插入的标准化行列表。

    Returns:
        int: 实际插入的记录数。
    """

    if not rows:
        return 0

    safe_table_name, _ = validate_mode_payload_table_name(table_name)
    qualified_table_name = quote_qualified_table(SCHEMA_NAME, safe_table_name)
    column_names = sorted({column for row in rows for column in row.keys()})
    placeholders = ", ".join(["?"] * len(column_names))
    insert_sql = f"""
        INSERT INTO {qualified_table_name} (
            {", ".join(quote_identifier(column_name) for column_name in column_names)}
        )
        VALUES ({placeholders})
    """

    payload_rows: list[tuple[Any, ...]] = []
    for row in rows:
        payload_rows.append(tuple(row.get(column_name) for column_name in column_names))

    with connect(db_path) as conn:
        conn.executemany(insert_sql, payload_rows)
        conn.commit()
    return len(payload_rows)


def refill_empty_mode_payload_table(
    db_path: str | Path,
    table_name: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """回填单张空的 `mode_payload_{x}` 表。

    Args:
        db_path: 数据库目标 DSN。
        table_name: 目标 `mode_payload_{x}` 表名。
        dry_run: 是否仅预览不实际插入。

    Returns:
        dict[str, Any]: 单表回填结果，包含命中的 `modes_id`、抓取记录数、补列数与插入数。
    """

    safe_table_name, modes_id = validate_mode_payload_table_name(table_name)
    current_rows = count_table_rows(db_path, safe_table_name)
    if current_rows > 0:
        return {
            "table_name": safe_table_name,
            "modes_id": modes_id,
            "status": "skip_non_empty",
            "current_rows": current_rows,
            "fetched_rows": 0,
            "added_columns": [],
            "inserted_rows": 0,
        }

    fetched_records = load_fetched_mode_records(db_path, modes_id)
    insert_rows, column_samples = build_insert_rows(fetched_records)

    if dry_run:
        missing_columns: list[str] = []
        with connect(db_path) as conn:
            existing_columns = set(conn.table_columns(safe_table_name))
            missing_columns = sorted(column for column in column_samples if column not in existing_columns)
        return {
            "table_name": safe_table_name,
            "modes_id": modes_id,
            "status": "dry_run",
            "current_rows": current_rows,
            "fetched_rows": len(fetched_records),
            "added_columns": missing_columns,
            "inserted_rows": len(insert_rows),
        }

    added_columns = ensure_table_columns(db_path, safe_table_name, column_samples)
    inserted_rows = bulk_insert_rows(db_path, safe_table_name, insert_rows)
    return {
        "table_name": safe_table_name,
        "modes_id": modes_id,
        "status": "filled" if inserted_rows > 0 else "no_source_records",
        "current_rows": current_rows,
        "fetched_rows": len(fetched_records),
        "added_columns": added_columns,
        "inserted_rows": inserted_rows,
    }


def refill_empty_mode_payload_tables(
    db_path: str | Path,
    dry_run: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    """批量回填全部空的 `public.mode_payload_{x}` 表。

    Args:
        db_path: 数据库目标 DSN。
        dry_run: 是否仅预览不执行写入。
        limit: 可选，限制最多处理多少张表，便于烟雾测试。

    Returns:
        dict[str, Any]: 批量执行结果汇总，包含逐表明细。

    Raises:
        ValueError: 当数据库目标不是 PostgreSQL 时抛出。
    """

    if detect_database_engine(db_path) != "postgres":
        raise ValueError("该脚本仅支持 PostgreSQL 数据库目标。")

    tables = list_public_mode_payload_tables(db_path)
    if limit is not None and limit > 0:
        tables = tables[:limit]

    details: list[dict[str, Any]] = []
    scanned_tables = 0
    empty_tables = 0
    filled_tables = 0
    inserted_rows = 0
    added_column_count = 0

    for table_name in tables:
        scanned_tables += 1
        table_rows = count_table_rows(db_path, table_name)
        if table_rows == 0:
            empty_tables += 1

        detail = refill_empty_mode_payload_table(
            db_path=db_path,
            table_name=table_name,
            dry_run=dry_run,
        )
        details.append(detail)

        inserted_rows += int(detail["inserted_rows"])
        added_column_count += len(detail["added_columns"])
        if detail["status"] in {"filled", "dry_run"} and detail["fetched_rows"] > 0:
            filled_tables += 1

        print(
            f"[{detail['status']}] {SCHEMA_NAME}.{detail['table_name']}: "
            f"modes_id={detail['modes_id']}, "
            f"source_rows={detail['fetched_rows']}, "
            f"added_columns={len(detail['added_columns'])}, "
            f"inserted_rows={detail['inserted_rows']}"
        )

    return {
        "db_path": str(db_path),
        "schema": SCHEMA_NAME,
        "dry_run": dry_run,
        "scanned_tables": scanned_tables,
        "empty_tables": empty_tables,
        "filled_tables": filled_tables,
        "inserted_rows": inserted_rows,
        "added_column_count": added_column_count,
        "details": details,
    }


def print_summary(result: dict[str, Any]) -> None:
    """打印批量回填结果汇总。

    Args:
        result: `refill_empty_mode_payload_tables()` 返回的结果字典。

    Returns:
        None: 仅输出汇总信息到控制台。
    """

    print("-" * 72)
    print("空 mode_payload 表回填完成")
    print(f"数据库: {result['db_path']}")
    print(f"Schema: {result['schema']}")
    print(f"模式: {'仅预览' if result['dry_run'] else '实际回填'}")
    print(f"扫描表数量: {result['scanned_tables']}")
    print(f"空表数量: {result['empty_tables']}")
    print(f"命中并回填数量: {result['filled_tables']}")
    print(f"新增列总数: {result['added_column_count']}")
    print(f"插入记录总数: {result['inserted_rows']}")
    print("-" * 72)


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。

    Args:
        无。

    Returns:
        argparse.ArgumentParser: 配置好的命令行解析器。
    """

    parser = argparse.ArgumentParser(
        description="检查 public.mode_payload_{x} 空表，并从 public.fetched_mode_records 回填数据。"
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
        help="仅预览不实际写入数据库。",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="可选，限制最多处理多少张表，便于烟雾测试。",
    )
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    summary = refill_empty_mode_payload_tables(
        db_path=args.db_path,
        dry_run=bool(args.dry_run),
        limit=args.limit,
    )
    print_summary(summary)
