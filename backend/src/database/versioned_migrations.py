"""Explicit schema migrations for PostgreSQL production deployments.

The HTTP API and scheduler worker only validate the migration ledger.  Schema
DDL is performed by the explicit ``python -m database.versioned_migrations``
command while holding a transaction-scoped PostgreSQL advisory lock.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from database.connection import connect, detect_database_engine, utc_now


MIGRATION_TABLE = "schema_migrations"
CURRENT_SCHEMA_VERSION = 1
ADVISORY_LOCK_KEY = 734_605_197


class SchemaMigrationRequired(RuntimeError):
    """Raised when a production runtime sees an un-migrated database."""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    apply: Callable[[Any], None]


def _create_migration_ledger(conn: Any) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {MIGRATION_TABLE} (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


def _baseline_schema(conn: Any) -> None:
    """Apply the existing schema bootstrap once under the migration lock."""
    from database.bootstrap import _apply_legacy_schema_bootstrap

    _apply_legacy_schema_bootstrap(conn)


def _reconcile_created_prediction_tables(conn: Any) -> None:
    """Create or align every public payload mirror during explicit migrations."""
    from utils.created_prediction_store import ensure_created_prediction_table

    table_names = set(conn.list_tables("mode_payload_"))
    if conn.table_exists("mode_payload_tables"):
        rows = conn.execute("SELECT table_name FROM mode_payload_tables ORDER BY modes_id").fetchall()
        for row in rows:
            table_name = str(row["table_name"] or "")
            if table_name and conn.table_exists(table_name):
                table_names.add(table_name)

    for table_name in sorted(table_names):
        if table_name == "mode_payload_tables":
            continue
        ensure_created_prediction_table(conn, table_name, commit=False)


MIGRATIONS: tuple[Migration, ...] = (
    Migration(1, "baseline_schema", _baseline_schema),
)


def _applied_versions(conn: Any) -> set[int]:
    rows = conn.execute(f"SELECT version FROM {MIGRATION_TABLE}").fetchall()
    return {int(row["version"]) for row in rows}


def run_migrations(db_path: str | Path) -> list[int]:
    """Apply pending PostgreSQL schema migrations under an advisory lock."""
    if detect_database_engine(db_path) != "postgres":
        raise RuntimeError("版本化迁移命令仅支持 PostgreSQL。SQLite 仅用于显式测试/bootstrap。")

    with connect(db_path) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(?)", (ADVISORY_LOCK_KEY,))
        _create_migration_ledger(conn)
        applied = _applied_versions(conn)
        newly_applied: list[int] = []
        for migration in MIGRATIONS:
            if migration.version in applied:
                continue
            migration.apply(conn)
            conn.execute(
                f"INSERT INTO {MIGRATION_TABLE} (version, name, applied_at) VALUES (?, ?, ?)",
                (migration.version, migration.name, utc_now()),
            )
            newly_applied.append(migration.version)
        _reconcile_created_prediction_tables(conn)
        return newly_applied


def validate_runtime_schema(db_path: str | Path) -> None:
    """Verify that an API/worker PostgreSQL target has all migrations applied."""
    if detect_database_engine(db_path) != "postgres":
        return

    expected = {migration.version for migration in MIGRATIONS}
    with connect(db_path) as conn:
        if not conn.table_exists(MIGRATION_TABLE):
            raise SchemaMigrationRequired(
                "数据库尚未执行版本化迁移；请先运行 python -m database.versioned_migrations。"
            )
        missing = expected - _applied_versions(conn)
    if missing:
        missing_text = ", ".join(str(version) for version in sorted(missing))
        raise SchemaMigrationRequired(
            f"数据库缺少 schema migration 版本 {missing_text}；"
            "请先运行 python -m database.versioned_migrations。"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply Liuhecai PostgreSQL schema migrations.")
    parser.add_argument("--db-path", "--db_path", dest="db_path", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    applied = run_migrations(args.db_path)
    if applied:
        print(f"Applied schema migrations: {', '.join(str(version) for version in applied)}")
    else:
        print("Schema migrations are already current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
