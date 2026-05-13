"""为缺少 type=3 + web_id=4 样本的 mode_payload 表回填数据。

用途：
1. 读取 `public.site_prediction_modules` 中启用的模块
2. 找到对应的 `default_modes_id` 与 `public.mode_payload_{x}` 表
3. 若目标表中不存在 `type=3 + web_id=4` 的样本数据
4. 则从 `public.fetched_mode_records` 提取该 `modes_id` 下 `web_id=4` 且 `payload_json.type=3` 的记录
5. 将 `payload_json` 展开为列，并批量写入对应 `public.mode_payload_{x}` 表

说明：
1. 该脚本不会清空已有数据，只会补写缺失的 type=3 + web_id=4 样本
2. `payload_json` 中的对象/数组会转成 JSON 字符串后落库
3. 若目标表缺失对应列，会先自动补列
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
PREDICT_ROOT = SRC_ROOT / "predict"

for path_item in (PREDICT_ROOT, SRC_ROOT):
    if str(path_item) not in sys.path:
        sys.path.insert(0, str(path_item))

from db import connect, default_postgres_target, detect_database_engine, quote_identifier  # noqa: E402
from mechanisms import PREDICTION_CONFIGS, build_title_prediction_configs  # noqa: E402


SCHEMA_NAME = "public"
FETCHED_RECORDS_TABLE = "fetched_mode_records"
SITE_MODULES_TABLE = "site_prediction_modules"
MODE_PAYLOAD_TABLE_RE = re.compile(r"^mode_payload_(\d+)$")
FORCED_LOTTERY_TYPE = 3
FORCED_WEB_ID = 4
RESERVED_COLUMN_FALLBACK = "value"

def default_db_target() -> str:
    """返回脚本默认使用的数据库目标。

    Args:
        无。

    Returns:
        str: 正式运行统一读取 `DATABASE_URL` 或 `config.yaml` 中的 PostgreSQL DSN。
    """
    return default_postgres_target()


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


def refresh_prediction_configs(db_path: str | Path) -> None:
    """刷新动态预测配置。

    Args:
        db_path: 数据库目标 DSN。

    Returns:
        None: 仅更新全局预测配置缓存。
    """

    PREDICTION_CONFIGS.update(build_title_prediction_configs(db_path))


def load_enabled_site_mode_tables(db_path: str | Path) -> list[dict[str, Any]]:
    """读取启用站点模块并解析出对应的 `mode_payload_{x}` 表。

    Args:
        db_path: 数据库目标 DSN。

    Returns:
        list[dict[str, Any]]: 去重后的启用模块信息列表。
    """

    refresh_prediction_configs(db_path)

    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT mechanism_key
            FROM site_prediction_modules
            WHERE COALESCE(status, 0) = 1
            ORDER BY mechanism_key
            """
        ).fetchall()

    result: list[dict[str, Any]] = []
    for row in rows:
        mechanism_key = str(row["mechanism_key"] or "").strip()
        if not mechanism_key or mechanism_key not in PREDICTION_CONFIGS:
            continue
        config = PREDICTION_CONFIGS[mechanism_key]
        table_name = str(config.default_table or f"mode_payload_{config.default_modes_id}")
        _, modes_id = validate_mode_payload_table_name(table_name)
        result.append(
            {
                "mechanism_key": mechanism_key,
                "title": str(config.title or ""),
                "modes_id": int(config.default_modes_id),
                "table_name": table_name,
                "table_modes_id": modes_id,
            }
        )
    return result


def count_type3_web4_rows(db_path: str | Path, table_name: str) -> int:
    """统计目标表中 `type=3 + web_id=4` 的记录数。

    Args:
        db_path: 数据库目标 DSN。
        table_name: 目标 `mode_payload_{x}` 表名。

    Returns:
        int: 命中记录数。
    """

    safe_table_name, _ = validate_mode_payload_table_name(table_name)
    qualified_table_name = quote_qualified_table(SCHEMA_NAME, safe_table_name)

    with connect(db_path) as conn:
        if not conn.table_exists(safe_table_name):
            return 0

        columns = set(conn.table_columns(safe_table_name))
        filters = ["CAST(type AS INTEGER) = ?"]
        params: list[Any] = [FORCED_LOTTERY_TYPE]

        if "web" in columns:
            filters.append("CAST(web AS INTEGER) = ?")
            params.append(FORCED_WEB_ID)
        elif "web_id" in columns:
            filters.append("CAST(web_id AS INTEGER) = ?")
            params.append(FORCED_WEB_ID)
        else:
            return 0

        row = conn.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM {qualified_table_name}
            WHERE {" AND ".join(filters)}
            """,
            params,
        ).fetchone()
    return int(row["total"] or 0) if row else 0


def load_fetched_type3_web4_records(db_path: str | Path, modes_id: int) -> list[dict[str, Any]]:
    """读取指定 `modes_id` 的 `type=3 + web_id=4` 抓取记录。

    Args:
        db_path: 数据库目标 DSN。
        modes_id: 需要提取的玩法 ID。

    Returns:
        list[dict[str, Any]]: 已过滤后的抓取记录列表。
    """

    with connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT web_id, modes_id, source_record_id, year, term, fetched_at, payload_json
            FROM {quote_identifier(FETCHED_RECORDS_TABLE)}
            WHERE modes_id = ?
              AND web_id = ?
            ORDER BY
                CAST(COALESCE(NULLIF(CAST(year AS TEXT), ''), '0') AS INTEGER),
                CAST(COALESCE(NULLIF(CAST(term AS TEXT), ''), '0') AS INTEGER),
                CAST(COALESCE(NULLIF(CAST(source_record_id AS TEXT), ''), '0') AS INTEGER)
            """,
            (modes_id, FORCED_WEB_ID),
        ).fetchall()

    result: list[dict[str, Any]] = []
    for row in rows:
        payload = json.loads(str(row["payload_json"] or "{}"))
        if str((payload or {}).get("type", "")) != str(FORCED_LOTTERY_TYPE):
            continue
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
    """将抓取记录转换为待插入行数据。

    Args:
        records: 已过滤过 `type=3 + web_id=4` 的抓取记录。

    Returns:
        tuple[list[dict[str, Any]], dict[str, list[Any]]]:
            第一个值是标准化后的待插入行列表，
            第二个值是“列名 -> 样本值列表”的映射。
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
        column_samples: “列名 -> 样本值列表”的映射。

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

    payload_rows = [tuple(row.get(column_name) for column_name in column_names) for row in rows]
    with connect(db_path) as conn:
        conn.executemany(insert_sql, payload_rows)
        conn.commit()
    return len(payload_rows)


def backfill_one_mode_payload_table(
    db_path: str | Path,
    module_entry: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any]:
    """回填单个缺少 `type=3 + web_id=4` 样本的表。

    Args:
        db_path: 数据库目标 DSN。
        module_entry: 单个站点模块信息。
        dry_run: 是否仅预览不实际写入。

    Returns:
        dict[str, Any]: 单表回填结果。
    """

    table_name = str(module_entry["table_name"])
    modes_id = int(module_entry["modes_id"])
    existing_count = count_type3_web4_rows(db_path, table_name)
    if existing_count > 0:
        return {
            **module_entry,
            "status": "skip_existing",
            "existing_type3_web4_rows": existing_count,
            "source_rows": 0,
            "added_columns": [],
            "inserted_rows": 0,
        }

    records = load_fetched_type3_web4_records(db_path, modes_id)
    insert_rows, column_samples = build_insert_rows(records)

    if dry_run:
        missing_columns: list[str] = []
        with connect(db_path) as conn:
            existing_columns = set(conn.table_columns(table_name)) if conn.table_exists(table_name) else set()
            missing_columns = sorted(column for column in column_samples if column not in existing_columns)
        return {
            **module_entry,
            "status": "dry_run" if records else "no_source_records",
            "existing_type3_web4_rows": existing_count,
            "source_rows": len(records),
            "added_columns": missing_columns,
            "inserted_rows": len(insert_rows),
        }

    if not records:
        return {
            **module_entry,
            "status": "no_source_records",
            "existing_type3_web4_rows": existing_count,
            "source_rows": 0,
            "added_columns": [],
            "inserted_rows": 0,
        }

    added_columns = ensure_table_columns(db_path, table_name, column_samples)
    inserted_rows = bulk_insert_rows(db_path, table_name, insert_rows)
    return {
        **module_entry,
        "status": "filled",
        "existing_type3_web4_rows": existing_count,
        "source_rows": len(records),
        "added_columns": added_columns,
        "inserted_rows": inserted_rows,
    }


def backfill_missing_type3_web4_samples(
    db_path: str | Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """批量回填站点模块缺失的 `type=3 + web_id=4` 样本。

    Args:
        db_path: 数据库目标 DSN。
        dry_run: 是否仅预览不执行写入。

    Returns:
        dict[str, Any]: 批量回填结果汇总。

    Raises:
        ValueError: 当数据库目标不是 PostgreSQL 时抛出。
    """

    if detect_database_engine(db_path) != "postgres":
        raise ValueError("该脚本仅支持 PostgreSQL 数据库目标。")

    module_entries = load_enabled_site_mode_tables(db_path)
    details: list[dict[str, Any]] = []
    summary = {
        "total_modules": len(module_entries),
        "filled": 0,
        "skip_existing": 0,
        "no_source_records": 0,
        "dry_run": 0,
        "inserted_rows": 0,
        "added_columns": 0,
    }

    for module_entry in module_entries:
        detail = backfill_one_mode_payload_table(
            db_path=db_path,
            module_entry=module_entry,
            dry_run=dry_run,
        )
        details.append(detail)
        status = str(detail["status"])
        if status in summary:
            summary[status] += 1
        summary["inserted_rows"] += int(detail["inserted_rows"])
        summary["added_columns"] += len(detail["added_columns"])
        print(
            f"[{status}] {SCHEMA_NAME}.{detail['table_name']}: "
            f"key={detail['mechanism_key']}, modes_id={detail['modes_id']}, "
            f"source_rows={detail['source_rows']}, "
            f"added_columns={len(detail['added_columns'])}, "
            f"inserted_rows={detail['inserted_rows']}"
        )

    return {
        "db_path": str(db_path),
        "lottery_type": FORCED_LOTTERY_TYPE,
        "web_id": FORCED_WEB_ID,
        "dry_run": dry_run,
        "summary": summary,
        "details": details,
    }


def print_summary(report: dict[str, Any]) -> None:
    """打印回填结果汇总。

    Args:
        report: `backfill_missing_type3_web4_samples()` 返回的报告。

    Returns:
        None: 仅输出汇总信息到控制台。
    """

    summary = report["summary"]
    print("-" * 72)
    print("type=3 + web_id=4 样本回填完成")
    print(f"数据库: {report['db_path']}")
    print(f"模式: {'仅预览' if report['dry_run'] else '实际回填'}")
    print(f"目标模块数: {summary['total_modules']}")
    print(f"已存在样本: {summary['skip_existing']}")
    print(f"完成回填: {summary['filled']}")
    print(f"无源数据: {summary['no_source_records']}")
    print(f"新增列总数: {summary['added_columns']}")
    print(f"插入记录总数: {summary['inserted_rows']}")
    print("-" * 72)


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。

    Args:
        无。

    Returns:
        argparse.ArgumentParser: 配置好的命令行解析器。
    """

    parser = argparse.ArgumentParser(
        description="为 site_prediction_modules 对应的 mode_payload 表补齐 type=3 + web_id=4 样本。"
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
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    report = backfill_missing_type3_web4_samples(
        db_path=args.db_path,
        dry_run=bool(args.dry_run),
    )
    print_summary(report)
