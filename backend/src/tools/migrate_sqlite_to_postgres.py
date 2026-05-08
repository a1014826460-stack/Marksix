"""Copy the existing Liuhecai SQLite database into PostgreSQL.

这不是重新抓取或重新生成数据，而是直接把当前 SQLite 里的历史数据、后台配置、
归一化表和文本映射表整体迁到 PostgreSQL，方便多站点和多模块部署时继续沿用现有数据。
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import psycopg


DEFAULT_SOURCE = Path(__file__).resolve().parents[2] / "data" / "lottery_modes.sqlite3"


def quote_identifier(identifier: str) -> str:
    return '"' + str(identifier).replace('"', '""') + '"'


def transform_table_ddl(sql_text: str) -> str:
    """把 SQLite CREATE TABLE 语句转成 PostgreSQL 可执行版本。

    当前库表结构比较规整，主要差异集中在自增主键。这里按最小变更策略处理，
    这样能最大限度保留原表约束、唯一索引和外键定义。
    """
    transformed = sql_text
    transformed = re.sub(
        r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b",
        "BIGSERIAL PRIMARY KEY",
        transformed,
        flags=re.IGNORECASE,
    )
    transformed = re.sub(
        r"\bINTEGER\s+PRIMARY\s+KEY\b",
        "BIGINT PRIMARY KEY",
        transformed,
        flags=re.IGNORECASE,
    )
    transformed = re.sub(r"\bAUTOINCREMENT\b", "", transformed, flags=re.IGNORECASE)
    return transformed


def fetch_tables(source: sqlite3.Connection) -> list[dict[str, str]]:
    rows = source.execute(
        """
        SELECT name, sql
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
          AND sql IS NOT NULL
        ORDER BY name
        """
    ).fetchall()
    return [{"name": row["name"], "sql": row["sql"]} for row in rows]


def fetch_indexes(source: sqlite3.Connection) -> list[dict[str, str]]:
    rows = source.execute(
        """
        SELECT name, tbl_name, sql
        FROM sqlite_master
        WHERE type = 'index'
          AND name NOT LIKE 'sqlite_%'
          AND sql IS NOT NULL
        ORDER BY name
        """
    ).fetchall()
    return [{"name": row["name"], "table_name": row["tbl_name"], "sql": row["sql"]} for row in rows]


def referenced_tables(sql_text: str) -> set[str]:
    return {
        match.group(1)
        for match in re.finditer(
            r"REFERENCES\s+\"?([A-Za-z0-9_]+)\"?",
            sql_text,
            flags=re.IGNORECASE,
        )
    }


def sort_tables_by_dependencies(tables: list[dict[str, str]]) -> list[dict[str, str]]:
    """Create PostgreSQL tables in foreign-key-safe order.

    SQLite stores tables alphabetically in `sqlite_master` when we query them
    with ORDER BY name, but PostgreSQL requires referenced tables to exist when
    a foreign key is declared. We therefore topologically sort by REFERENCES.
    """
    table_names = {table["name"] for table in tables}
    dependencies: dict[str, set[str]] = {}
    reverse_edges: dict[str, set[str]] = defaultdict(set)

    for table in tables:
        refs = referenced_tables(table["sql"]) & table_names
        dependencies[table["name"]] = set(refs)
        for ref in refs:
            reverse_edges[ref].add(table["name"])

    ready = deque(sorted(name for name, refs in dependencies.items() if not refs))
    ordered_names: list[str] = []

    while ready:
        name = ready.popleft()
        ordered_names.append(name)
        for dependent in sorted(reverse_edges.get(name, set())):
            remaining = dependencies[dependent]
            remaining.discard(name)
            if not remaining:
                ready.append(dependent)

    if len(ordered_names) != len(tables):
        unresolved = sorted(set(table_names) - set(ordered_names))
        raise RuntimeError(
            "Could not determine a safe table creation order for PostgreSQL. "
            f"Unresolved tables: {', '.join(unresolved)}"
        )

    table_by_name = {table["name"]: table for table in tables}
    return [table_by_name[name] for name in ordered_names]


def table_columns(source: sqlite3.Connection, table_name: str) -> list[str]:
    rows = source.execute(f"PRAGMA table_info({quote_identifier(table_name)})").fetchall()
    return [str(row["name"]) for row in rows]


def drop_target_objects(target: psycopg.Connection, table_names: list[str]) -> None:
    """按逆序删除表，避免外键依赖阻塞重建。"""
    with target.cursor() as cursor:
        for table_name in reversed(table_names):
            cursor.execute(f"DROP TABLE IF EXISTS {quote_identifier(table_name)} CASCADE")
    target.commit()


def create_target_tables(target: psycopg.Connection, tables: list[dict[str, str]]) -> None:
    with target.cursor() as cursor:
        for table in tables:
            cursor.execute(transform_table_ddl(table["sql"]))
    target.commit()


def create_target_indexes(target: psycopg.Connection, indexes: list[dict[str, str]]) -> None:
    with target.cursor() as cursor:
        for index in indexes:
            cursor.execute(index["sql"])
    target.commit()


def reset_postgres_sequences(target: psycopg.Connection, tables: list[dict[str, str]]) -> None:
    """Advance BIGSERIAL sequences to the current max(id) after explicit inserts."""
    with target.cursor() as cursor:
        for table in tables:
            table_name = table["name"]
            cursor.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = %s
                  AND column_name = 'id'
                """,
                (table_name,),
            )
            if cursor.fetchone() is None:
                continue

            cursor.execute(
                """
                SELECT pg_get_serial_sequence(%s, 'id')
                """,
                (table_name,),
            )
            row = cursor.fetchone()
            sequence_name = row[0] if row else None
            if not sequence_name:
                continue

            cursor.execute(
                f"SELECT COALESCE(MAX(id), 0) FROM {quote_identifier(table_name)}"
            )
            max_id = int(cursor.fetchone()[0] or 0)
            if max_id > 0:
                cursor.execute("SELECT setval(%s, %s, %s)", (sequence_name, max_id, True))
            else:
                # Empty tables should keep their next generated id at 1.
                cursor.execute("ALTER SEQUENCE " + sequence_name + " RESTART WITH 1")
    target.commit()


def copy_table_rows(
    source: sqlite3.Connection,
    target: psycopg.Connection,
    table_name: str,
    batch_size: int,
) -> int:
    columns = table_columns(source, table_name)
    if not columns:
        return 0

    column_sql = ", ".join(quote_identifier(column) for column in columns)
    placeholder_sql = ", ".join(["%s"] * len(columns))
    insert_sql = (
        f"INSERT INTO {quote_identifier(table_name)} ({column_sql}) "
        f"VALUES ({placeholder_sql})"
    )

    total = 0
    with target.cursor() as cursor:
        cursor.execute(f"DELETE FROM {quote_identifier(table_name)}")

        source_cursor = source.execute(f"SELECT {column_sql} FROM {quote_identifier(table_name)}")
        while True:
            rows = source_cursor.fetchmany(batch_size)
            if not rows:
                break
            values = [tuple(row[column] for column in columns) for row in rows]
            cursor.executemany(insert_sql, values)
            total += len(values)

    target.commit()
    return total


def migrate_sqlite_to_postgres(
    source_sqlite: str | Path,
    target_dsn: str,
    *,
    batch_size: int = 500,
    drop_existing: bool = False,
) -> dict[str, Any]:
    source_path = Path(source_sqlite)
    if not source_path.exists():
        raise FileNotFoundError(f"SQLite source does not exist: {source_path}")
    if not target_dsn.strip():
        raise ValueError("target_dsn cannot be empty")

    source = sqlite3.connect(source_path)
    source.row_factory = sqlite3.Row
    source.execute("PRAGMA foreign_keys = OFF")

    try:
        tables = sort_tables_by_dependencies(fetch_tables(source))
        indexes = fetch_indexes(source)
        with psycopg.connect(target_dsn) as target:
            if drop_existing:
                drop_target_objects(target, [table["name"] for table in tables])

            create_target_tables(target, tables)

            table_counts: dict[str, int] = {}
            for table in tables:
                copied = copy_table_rows(source, target, table["name"], batch_size)
                table_counts[table["name"]] = copied

            create_target_indexes(target, indexes)
            reset_postgres_sequences(target, tables)

        return {
            "source_sqlite": str(source_path),
            "target_dsn": target_dsn,
            "table_count": len(tables),
            "index_count": len(indexes),
            "copied_rows": table_counts,
        }
    finally:
        source.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migrate the existing Liuhecai SQLite database into PostgreSQL."
    )
    parser.add_argument(
        "--source-sqlite",
        default=str(DEFAULT_SOURCE),
        help="Path to the existing SQLite database file.",
    )
    parser.add_argument(
        "--target-dsn",
        required=True,
        help="PostgreSQL DSN, for example postgresql://user:pass@host:5432/dbname",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="How many rows to copy per batch.",
    )
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Drop target tables before recreating them. Use this when rerunning a full migration.",
    )
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    result = migrate_sqlite_to_postgres(
        args.source_sqlite,
        args.target_dsn,
        batch_size=args.batch_size,
        drop_existing=args.drop_existing,
    )
    print(result)
