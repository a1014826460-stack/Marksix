"""PostgreSQL-backed static JSON mapping import and query services."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
import yaml
from psycopg.rows import dict_row

from core.errors import AppError, ValidationError
from db import connect, default_postgres_target, is_postgres_target, quote_identifier
from logger import get_logger, init_logging
from runtime_config import get_bootstrap_config_value

LOGGER = get_logger("domains.static_mappings")
BACKEND_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = BACKEND_ROOT / "config" / "static_mappings.yaml"
DEFAULT_SCHEMA = "public"
DEFAULT_TABLE_PREFIX = "static_mapping_"
DEFAULT_PATH_PREFIX = "json_data"


class StaticMappingError(AppError):
    """Base exception for static mapping import and query failures."""

    status_code = 500
    code = "STATIC_MAPPING_ERROR"


@dataclass(frozen=True)
class StaticMappingDatasetConfig:
    """Dataset-level import metadata."""

    name: str
    json_path: Path
    table_name: str
    path_prefix: str = DEFAULT_PATH_PREFIX
    key_field: str = "id"
    path_field: str = "mapping_path"


@dataclass(frozen=True)
class StaticMappingImportConfig:
    """Resolved import configuration."""

    db_target: str
    schema_name: str
    datasets: tuple[StaticMappingDatasetConfig, ...]
    incremental: bool = False


@dataclass(frozen=True)
class StaticMappingRecord:
    """Serializable static mapping record."""

    dataset: str
    mapping_path: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class MappingImportReport:
    """Import summary for one dataset."""

    dataset: str
    table_name: str
    total_rows: int
    inserted_rows: int
    updated_rows: int
    failed_rows: int
    replaced: bool


def _default_db_target() -> str:
    env_target = str(get_bootstrap_config_value("database.default_postgres_dsn", "") or "").strip()
    if env_target:
        return env_target
    env_url = os.getenv("DATABASE_URL", "").strip()
    if env_url:
        return env_url
    try:
        return default_postgres_target()
    except RuntimeError:
        return ""


def _build_db_target(
    *,
    db_url: str = "",
    host: str = "",
    port: str = "",
    db_name: str = "",
    user: str = "",
    password: str = "",
) -> str:
    if db_url.strip():
        return db_url.strip()
    if not any([host, port, db_name, user, password]):
        return ""
    if not all([host, port, db_name, user]):
        raise ValidationError("数据库连接参数不完整。使用拆分字段时至少需要 host、port、name、user。")
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"


def _ensure_postgres_target(db_target: str) -> str:
    target = str(db_target or "").strip()
    if not target:
        raise ValidationError("缺少 PostgreSQL 连接信息。请通过 --db-target、配置文件或 DATABASE_URL 提供。")
    if not is_postgres_target(target):
        raise ValidationError("静态映射功能仅支持 PostgreSQL 目标。")
    return target


def _validate_identifier(name: str, *, field_name: str) -> str:
    value = str(name or "").strip()
    if not value:
        raise ValidationError(f"{field_name} 不能为空。")
    if not value.replace("_", "").isalnum() or value[0].isdigit():
        raise ValidationError(f"{field_name} 非法: {value}")
    return value.lower()


def _build_dataset_path(dataset_name: str, record_key: Any, path_prefix: str) -> str:
    return f"{path_prefix.strip('/')}/{dataset_name}/{record_key}"


def _load_yaml_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise ValidationError(f"配置文件不存在: {config_path}")
    try:
        raw_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValidationError(f"配置文件解析失败: {config_path}") from exc
    if not isinstance(raw_data, dict):
        raise ValidationError("配置文件根节点必须为对象。")
    return raw_data


def _resolve_json_path(path_value: str | None) -> Path:
    if not path_value:
        raise ValidationError("dataset.json_path 不能为空。")
    path = Path(path_value)
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    return path.resolve()


def _normalize_dataset_config(item: dict[str, Any]) -> StaticMappingDatasetConfig:
    name = _validate_identifier(str(item.get("name") or "").strip(), field_name="dataset.name")
    table_name = _validate_identifier(
        str(item.get("table_name") or f"{DEFAULT_TABLE_PREFIX}{name}"),
        field_name="dataset.table_name",
    )
    path_prefix = str(item.get("path_prefix") or DEFAULT_PATH_PREFIX).strip().strip("/")
    key_field = str(item.get("key_field") or "id").strip()
    path_field = str(item.get("path_field") or "mapping_path").strip()
    if not key_field:
        raise ValidationError(f"{name} 的 key_field 不能为空。")
    if not path_field:
        raise ValidationError(f"{name} 的 path_field 不能为空。")
    return StaticMappingDatasetConfig(
        name=name,
        json_path=_resolve_json_path(str(item.get("json_path") or "")),
        table_name=table_name,
        path_prefix=path_prefix or DEFAULT_PATH_PREFIX,
        key_field=key_field,
        path_field=path_field,
    )


def load_import_config(
    *,
    config_path: str | Path | None = None,
    db_target: str | None = None,
    db_host: str | None = None,
    db_port: str | None = None,
    db_name: str | None = None,
    db_user: str | None = None,
    db_password: str | None = None,
    incremental: bool = False,
) -> StaticMappingImportConfig:
    """Load static mapping import config from YAML and runtime defaults."""

    resolved_config_path = Path(config_path).resolve() if config_path else DEFAULT_CONFIG_PATH
    raw_config = _load_yaml_config(resolved_config_path)
    db_section = raw_config.get("database") or {}
    mappings_section = raw_config.get("static_mappings") or {}

    configured_target = (
        _build_db_target(
            db_url=str(db_target or "").strip(),
            host=str(db_host or "").strip(),
            port=str(db_port or "").strip(),
            db_name=str(db_name or "").strip(),
            user=str(db_user or "").strip(),
            password=str(db_password or "").strip(),
        )
        or _build_db_target(
            db_url=str(db_section.get("url") or "").strip(),
            host=str(db_section.get("host") or "").strip(),
            port=str(db_section.get("port") or "").strip(),
            db_name=str(db_section.get("name") or "").strip(),
            user=str(db_section.get("user") or "").strip(),
            password=str(db_section.get("password") or "").strip(),
        )
        or _default_db_target()
    )
    schema_name = _validate_identifier(
        str(db_section.get("schema") or mappings_section.get("schema") or DEFAULT_SCHEMA),
        field_name="schema",
    )

    dataset_items = mappings_section.get("datasets")
    if not isinstance(dataset_items, list) or not dataset_items:
        raise ValidationError("配置文件 static_mappings.datasets 至少需要定义一个数据集。")

    datasets = tuple(_normalize_dataset_config(item) for item in dataset_items if isinstance(item, dict))
    if not datasets:
        raise ValidationError("未能从配置文件中解析出有效的数据集配置。")

    return StaticMappingImportConfig(
        db_target=_ensure_postgres_target(configured_target),
        schema_name=schema_name,
        datasets=datasets,
        incremental=incremental,
    )


def _read_json_records(dataset: StaticMappingDatasetConfig) -> list[dict[str, Any]]:
    if not dataset.json_path.exists():
        raise ValidationError(f"{dataset.name} 源文件不存在: {dataset.json_path}")
    if dataset.json_path.stat().st_size <= 0:
        raise ValidationError(f"{dataset.name} 源文件为空: {dataset.json_path}")

    try:
        payload = json.loads(dataset.json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{dataset.name} JSON 解析失败: {dataset.json_path}") from exc

    if not isinstance(payload, list):
        raise ValidationError(f"{dataset.name} JSON 根节点必须为数组。")
    if not payload:
        raise ValidationError(f"{dataset.name} JSON 数据为空数组。")

    normalized: list[dict[str, Any]] = []
    expected_keys: set[str] | None = None
    seen_keys: set[str] = set()

    for index, row in enumerate(payload, start=1):
        if not isinstance(row, dict):
            raise ValidationError(f"{dataset.name} 第 {index} 行不是对象。")
        if dataset.key_field not in row:
            raise ValidationError(f"{dataset.name} 第 {index} 行缺少主键字段 {dataset.key_field}。")
        row_key = row.get(dataset.key_field)
        if row_key in (None, ""):
            raise ValidationError(f"{dataset.name} 第 {index} 行主键字段 {dataset.key_field} 为空。")
        row_keys = set(row.keys())
        if expected_keys is None:
            expected_keys = row_keys
        elif row_keys != expected_keys:
            raise ValidationError(
                f"{dataset.name} 第 {index} 行字段不完整或不一致。预期 {sorted(expected_keys)}，实际 {sorted(row_keys)}。"
            )
        unique_key = str(row_key)
        if unique_key in seen_keys:
            raise ValidationError(f"{dataset.name} 存在重复主键值: {unique_key}")
        seen_keys.add(unique_key)

        normalized_row = dict(row)
        normalized_row[dataset.path_field] = _build_dataset_path(dataset.name, row_key, dataset.path_prefix)
        normalized.append(normalized_row)

    return normalized


def _infer_column_sql_type(values: list[Any]) -> str:
    non_null_values = [value for value in values if value is not None]
    if not non_null_values:
        return "TEXT"
    if all(isinstance(value, bool) for value in non_null_values):
        return "BOOLEAN"
    if all(isinstance(value, int) and not isinstance(value, bool) for value in non_null_values):
        return "BIGINT"
    if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in non_null_values):
        return "DOUBLE PRECISION"
    return "TEXT"


def _serialize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def _schema_table_exists(conn: Any, schema_name: str, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = ?
          AND table_name = ?
        LIMIT 1
        """,
        (schema_name, table_name),
    ).fetchone()
    return bool(row)


def _schema_table_columns(conn: Any, schema_name: str, table_name: str) -> set[str]:
    rows = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = ?
          AND table_name = ?
        ORDER BY ordinal_position
        """,
        (schema_name, table_name),
    ).fetchall()
    return {str(row["column_name"]) for row in rows}


def _ensure_table(conn: Any, schema_name: str, dataset: StaticMappingDatasetConfig, records: list[dict[str, Any]]) -> tuple[str, list[str]]:
    column_names = list(records[0].keys())
    table_identifier = f"{schema_name}.{dataset.table_name}"
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {quote_identifier(schema_name)}")

    if _schema_table_exists(conn, schema_name, dataset.table_name):
        existing_columns = _schema_table_columns(conn, schema_name, dataset.table_name)
        for column_name in column_names:
            if column_name in existing_columns:
                continue
            sql_type = _infer_column_sql_type([record.get(column_name) for record in records])
            not_null = " NOT NULL DEFAULT ''" if column_name in {dataset.path_field} else ""
            conn.execute(
                f"ALTER TABLE {quote_identifier(schema_name)}.{quote_identifier(dataset.table_name)} "
                f"ADD COLUMN {quote_identifier(column_name)} {sql_type}{not_null}"
            )
    else:
        column_defs: list[str] = []
        for column_name in column_names:
            sql_type = _infer_column_sql_type([record.get(column_name) for record in records])
            not_null = " NOT NULL" if column_name in {dataset.key_field, dataset.path_field} else ""
            column_defs.append(f"{quote_identifier(column_name)} {sql_type}{not_null}")

        create_sql = (
            f"CREATE TABLE {quote_identifier(schema_name)}.{quote_identifier(dataset.table_name)} "
            f"({', '.join(column_defs)}, "
            f"PRIMARY KEY ({quote_identifier(dataset.key_field)}), "
            f"UNIQUE ({quote_identifier(dataset.path_field)}))"
        )
        conn.execute(create_sql)
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS {quote_identifier(f'idx_{dataset.table_name}_{dataset.path_field}')} "
        f"ON {quote_identifier(schema_name)}.{quote_identifier(dataset.table_name)} "
        f"({quote_identifier(dataset.path_field)})"
    )
    return table_identifier, column_names


def _truncate_table(conn: Any, schema_name: str, table_name: str) -> None:
    conn.execute(
        f"TRUNCATE TABLE {quote_identifier(schema_name)}.{quote_identifier(table_name)} RESTART IDENTITY"
    )


def _upsert_records(
    conn: Any,
    *,
    schema_name: str,
    dataset: StaticMappingDatasetConfig,
    column_names: list[str],
    records: list[dict[str, Any]],
) -> tuple[int, int, int]:
    insert_columns = ", ".join(quote_identifier(column_name) for column_name in column_names)
    placeholders = ", ".join(["?"] * len(column_names))
    update_columns = [
        column_name
        for column_name in column_names
        if column_name != dataset.key_field
    ]
    update_set_sql = ", ".join(
        f"{quote_identifier(column_name)} = EXCLUDED.{quote_identifier(column_name)}"
        for column_name in update_columns
    )

    sql_text = (
        f"INSERT INTO {quote_identifier(schema_name)}.{quote_identifier(dataset.table_name)} "
        f"({insert_columns}) VALUES ({placeholders}) "
        f"ON CONFLICT ({quote_identifier(dataset.key_field)}) DO UPDATE SET {update_set_sql}"
    )

    inserted_rows = 0
    updated_rows = 0
    failed_rows = 0

    existing_keys_rows = conn.execute(
        f"SELECT {quote_identifier(dataset.key_field)} FROM {quote_identifier(schema_name)}.{quote_identifier(dataset.table_name)}"
    ).fetchall()
    existing_keys = {str(row[dataset.key_field]) for row in existing_keys_rows}

    for index, record in enumerate(records, start=1):
        values = tuple(_serialize_value(record.get(column_name)) for column_name in column_names)
        try:
            conn.execute(sql_text, values)
            record_key = str(record.get(dataset.key_field))
            if record_key in existing_keys:
                updated_rows += 1
            else:
                inserted_rows += 1
                existing_keys.add(record_key)
        except Exception as exc:  # pragma: no cover - DB driver details vary
            failed_rows += 1
            LOGGER.exception(
                "static mapping row import failed",
                extra={
                    "result": {
                        "dataset": dataset.name,
                        "table_name": dataset.table_name,
                        "row_number": index,
                        "record_key": record.get(dataset.key_field),
                        "error": str(exc),
                    },
                },
            )

    return inserted_rows, updated_rows, failed_rows


def import_static_mappings(config: StaticMappingImportConfig) -> list[MappingImportReport]:
    """Import JSON datasets into PostgreSQL static mapping tables."""

    init_logging(config.db_target)
    reports: list[MappingImportReport] = []

    try:
        with connect(config.db_target) as conn:
            for dataset in config.datasets:
                records = _read_json_records(dataset)
                _, column_names = _ensure_table(conn, config.schema_name, dataset, records)
                if not config.incremental:
                    _truncate_table(conn, config.schema_name, dataset.table_name)
                inserted_rows, updated_rows, failed_rows = _upsert_records(
                    conn,
                    schema_name=config.schema_name,
                    dataset=dataset,
                    column_names=column_names,
                    records=records,
                )
                report = MappingImportReport(
                    dataset=dataset.name,
                    table_name=f"{config.schema_name}.{dataset.table_name}",
                    total_rows=len(records),
                    inserted_rows=inserted_rows,
                    updated_rows=updated_rows,
                    failed_rows=failed_rows,
                    replaced=not config.incremental,
                )
                LOGGER.info(
                    "static mapping import completed",
                    extra={
                        "result": {
                            "dataset": report.dataset,
                            "table_name": report.table_name,
                            "total_rows": report.total_rows,
                            "inserted_rows": report.inserted_rows,
                            "updated_rows": report.updated_rows,
                            "failed_rows": report.failed_rows,
                            "replaced": report.replaced,
                        },
                    },
                )
                reports.append(report)
    except ValidationError:
        raise
    except Exception as exc:
        raise StaticMappingError(f"静态映射导入失败: {exc}") from exc

    return reports


class MappingReader:
    """Reusable PostgreSQL reader for static mapping tables."""

    def __init__(
        self,
        *,
        db_target: str,
        schema_name: str,
        dataset_table_map: dict[str, str],
        path_field: str = "mapping_path",
    ):
        self.db_target = _ensure_postgres_target(db_target)
        self.schema_name = _validate_identifier(schema_name, field_name="schema_name")
        self.dataset_table_map = {
            _validate_identifier(dataset_name, field_name="dataset_name"): _validate_identifier(
                table_name,
                field_name=f"table_name({dataset_name})",
            )
            for dataset_name, table_name in dataset_table_map.items()
        }
        self.path_field = str(path_field or "mapping_path").strip()
        if not self.path_field:
            raise ValidationError("path_field 不能为空。")
        self._connections: dict[str, Any] = {}
        self._dataset_by_table = {table_name: dataset_name for dataset_name, table_name in self.dataset_table_map.items()}
        init_logging(self.db_target)

    def close(self) -> None:
        for conn in self._connections.values():
            conn.close()
        self._connections.clear()

    def __enter__(self) -> "MappingReader":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def _get_connection(self, dataset_name: str):
        conn = self._connections.get(dataset_name)
        if conn is None:
            try:
                conn = psycopg.connect(self.db_target, row_factory=dict_row, connect_timeout=10)
                conn.prepare_threshold = 1
            except Exception as exc:
                raise StaticMappingError(f"静态映射读取连接失败: {exc}") from exc
            self._connections[dataset_name] = conn
        return conn

    def _get_table_name(self, dataset_name: str) -> str:
        normalized_dataset = _validate_identifier(dataset_name, field_name="dataset_name")
        table_name = self.dataset_table_map.get(normalized_dataset)
        if not table_name:
            raise ValidationError(f"未配置的数据集: {dataset_name}")
        return table_name

    def get_mapping(self, dataset_name: str, path: str) -> dict[str, Any]:
        rows = self.batch_get_mappings(dataset_name, [path])
        if not rows:
            return {}
        return rows[0]

    def batch_get_mappings(self, dataset_name: str, paths: list[str]) -> list[dict[str, Any]]:
        normalized_paths = [str(path or "").strip() for path in paths if str(path or "").strip()]
        if not normalized_paths:
            return []
        try:
            table_name = self._get_table_name(dataset_name)
            conn = self._get_connection(dataset_name)
            rows = conn.execute(
                f"SELECT * FROM {quote_identifier(self.schema_name)}.{quote_identifier(table_name)} "
                f"WHERE {quote_identifier(self.path_field)} = ANY(%s) "
                f"ORDER BY {quote_identifier(self.path_field)}",
                (normalized_paths,),
            ).fetchall()
            return [dict(row) for row in rows]
        except AppError:
            raise
        except Exception as exc:
            raise StaticMappingError(f"静态映射读取失败: {exc}") from exc

    def infer_dataset_name(self, path: str) -> str:
        normalized_path = str(path or "").strip().strip("/")
        parts = normalized_path.split("/")
        if len(parts) >= 2 and parts[1] in self.dataset_table_map:
            return parts[1]
        raise ValidationError(f"无法从 path 推断数据集: {path}")

    def get_mapping_by_path(self, path: str) -> dict[str, Any]:
        return self.get_mapping(self.infer_dataset_name(path), path)

    def batch_get_mappings_by_path(self, paths: list[str]) -> list[dict[str, Any]]:
        grouped_paths: dict[str, list[str]] = defaultdict(list)
        for path in paths:
            normalized_path = str(path or "").strip()
            if not normalized_path:
                continue
            grouped_paths[self.infer_dataset_name(normalized_path)].append(normalized_path)

        result: list[dict[str, Any]] = []
        for dataset_name, dataset_paths in grouped_paths.items():
            result.extend(self.batch_get_mappings(dataset_name, dataset_paths))
        return result


def _load_reader_from_config(
    *,
    config_path: str | Path | None = None,
    db_target: str | None = None,
    db_host: str | None = None,
    db_port: str | None = None,
    db_name: str | None = None,
    db_user: str | None = None,
    db_password: str | None = None,
) -> MappingReader:
    config = load_import_config(
        config_path=config_path,
        db_target=db_target,
        db_host=db_host,
        db_port=db_port,
        db_name=db_name,
        db_user=db_user,
        db_password=db_password,
        incremental=True,
    )
    dataset_map = {dataset.name: dataset.table_name for dataset in config.datasets}
    return MappingReader(
        db_target=config.db_target,
        schema_name=config.schema_name,
        dataset_table_map=dataset_map,
    )


def get_mapping(
    path: str,
    *,
    dataset_name: str | None = None,
    config_path: str | Path | None = None,
    db_target: str | None = None,
    db_host: str | None = None,
    db_port: str | None = None,
    db_name: str | None = None,
    db_user: str | None = None,
    db_password: str | None = None,
) -> dict[str, Any]:
    """Get a single static mapping row by logical path."""

    with _load_reader_from_config(
        config_path=config_path,
        db_target=db_target,
        db_host=db_host,
        db_port=db_port,
        db_name=db_name,
        db_user=db_user,
        db_password=db_password,
    ) as reader:
        if dataset_name:
            return reader.get_mapping(dataset_name, path)
        return reader.get_mapping_by_path(path)


def batch_get_mappings(
    paths: list[str],
    *,
    dataset_name: str | None = None,
    config_path: str | Path | None = None,
    db_target: str | None = None,
    db_host: str | None = None,
    db_port: str | None = None,
    db_name: str | None = None,
    db_user: str | None = None,
    db_password: str | None = None,
) -> list[dict[str, Any]]:
    """Get multiple static mapping rows by logical path."""

    with _load_reader_from_config(
        config_path=config_path,
        db_target=db_target,
        db_host=db_host,
        db_port=db_port,
        db_name=db_name,
        db_user=db_user,
        db_password=db_password,
    ) as reader:
        if dataset_name:
            return reader.batch_get_mappings(dataset_name, paths)
        return reader.batch_get_mappings_by_path(paths)


def build_import_argument_parser() -> argparse.ArgumentParser:
    """Build CLI parser for the import script."""

    parser = argparse.ArgumentParser(description="Import static JSON mappings into PostgreSQL tables.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="YAML 配置文件路径。")
    parser.add_argument("--db-target", default="", help="PostgreSQL DSN，优先级高于配置文件。")
    parser.add_argument("--db-host", default="", help="PostgreSQL 主机名。")
    parser.add_argument("--db-port", default="", help="PostgreSQL 端口。")
    parser.add_argument("--db-name", default="", help="PostgreSQL 数据库名。")
    parser.add_argument("--db-user", default="", help="PostgreSQL 用户名。")
    parser.add_argument("--db-password", default="", help="PostgreSQL 密码。")
    parser.add_argument(
        "--incremental",
        action="store_true",
        default=False,
        help="增量导入模式，只插入新记录或更新已有记录。",
    )
    return parser


def build_reader_argument_parser() -> argparse.ArgumentParser:
    """Build CLI parser for the read script."""

    parser = argparse.ArgumentParser(description="Read static JSON mappings from PostgreSQL.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="YAML 配置文件路径。")
    parser.add_argument("--db-target", default="", help="PostgreSQL DSN，优先级高于配置文件。")
    parser.add_argument("--db-host", default="", help="PostgreSQL 主机名。")
    parser.add_argument("--db-port", default="", help="PostgreSQL 端口。")
    parser.add_argument("--db-name", default="", help="PostgreSQL 数据库名。")
    parser.add_argument("--db-user", default="", help="PostgreSQL 用户名。")
    parser.add_argument("--db-password", default="", help="PostgreSQL 密码。")
    parser.add_argument("--dataset", default="", help="数据集名称，例如 brain_test；留空时从 path 自动推断。")
    parser.add_argument("--path", default="", help="单个 mapping_path。")
    parser.add_argument("--paths", nargs="*", default=[], help="批量 mapping_path 列表。")
    return parser
