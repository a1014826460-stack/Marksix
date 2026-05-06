"""Database compatibility helpers for SQLite and PostgreSQL.

本项目原先完全基于 SQLite。为支持多站点、多模块并发管理，这里补一层
轻量数据库适配，尽量保持现有 SQL 写法不大改：

1. 默认仍兼容本地 SQLite 文件，方便开发和离线调试。
2. 当传入 PostgreSQL DSN，或环境变量 DATABASE_URL 存在时，自动切到 PostgreSQL。
3. 对 PostgreSQL 自动把 qmark 风格参数 `?` 转成 `%s`，减少现有业务 SQL 的改动量。
4. 提供表存在、列清单、表清单等跨数据库的元数据查询能力，替代 sqlite_master/PRAGMA。
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Sequence

import psycopg
from psycopg.rows import dict_row


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE_PATH = BACKEND_ROOT / "data" / "lottery_modes.sqlite3"
POSTGRES_SCHEMES = ("postgres://", "postgresql://")


def is_postgres_target(target: str | Path | None) -> bool:
    """判断目标是否为 PostgreSQL DSN。"""
    if target is None:
        return False
    return str(target).strip().lower().startswith(POSTGRES_SCHEMES)


def resolve_database_target(target: str | Path | None = None) -> str:
    """统一解析数据库目标。

    优先级：
    1. 显式传入的 PostgreSQL DSN
    2. 环境变量 DATABASE_URL
    3. 显式传入的 SQLite 路径
    4. 默认 SQLite 路径
    """
    if is_postgres_target(target):
        return str(target).strip()

    env_target = os.getenv("DATABASE_URL", "").strip()
    if env_target:
        return env_target

    if target is None:
        return str(DEFAULT_SQLITE_PATH)

    return str(Path(target))


def detect_database_engine(target: str | Path | None = None) -> str:
    """返回 `sqlite` 或 `postgres`。"""
    return "postgres" if is_postgres_target(resolve_database_target(target)) else "sqlite"


def quote_identifier(identifier: str) -> str:
    """安全引用表名/列名。"""
    return '"' + str(identifier).replace('"', '""') + '"'


def auto_increment_primary_key(column_name: str = "id", engine: str = "sqlite") -> str:
    """生成自增主键 SQL 片段。"""
    if engine == "postgres":
        return f"{quote_identifier(column_name)} BIGSERIAL PRIMARY KEY"
    return f"{quote_identifier(column_name)} INTEGER PRIMARY KEY AUTOINCREMENT"


def normalize_params(params: Any) -> Any:
    """把 list 等参数转换成驱动可接受的序列类型。"""
    if params is None:
        return ()
    if isinstance(params, tuple):
        return params
    if isinstance(params, list):
        return tuple(params)
    return params


def qmark_to_format(sql_text: str) -> str:
    """把 SQLite 的 `?` 占位符转换为 PostgreSQL `%s`。

    这里只做轻量语法扫描：忽略单引号、双引号中的 `?`，满足当前项目 SQL 即可。
    """
    result: list[str] = []
    in_single = False
    in_double = False
    index = 0

    while index < len(sql_text):
        char = sql_text[index]

        if char == "'" and not in_double:
            # 处理 SQL 单引号转义 ''
            if in_single and index + 1 < len(sql_text) and sql_text[index + 1] == "'":
                result.append("''")
                index += 2
                continue
            in_single = not in_single
            result.append(char)
            index += 1
            continue

        if char == '"' and not in_single:
            in_double = not in_double
            result.append(char)
            index += 1
            continue

        if char == "?" and not in_single and not in_double:
            result.append("%s")
        else:
            result.append(char)

        index += 1

    return "".join(result)


class CursorAdapter:
    """统一 sqlite3 / psycopg 游标接口。"""

    def __init__(self, cursor: Any):
        self._cursor = cursor

    @property
    def rowcount(self) -> int:
        return getattr(self._cursor, "rowcount", -1)

    def fetchone(self) -> Any:
        return self._cursor.fetchone()

    def fetchall(self) -> list[Any]:
        return self._cursor.fetchall()


class ConnectionAdapter:
    """统一数据库连接接口，屏蔽 SQLite / PostgreSQL 差异。"""

    def __init__(self, raw: Any, engine: str, target: str):
        self._raw = raw
        self.engine = engine
        self.target = target

    def __enter__(self) -> "ConnectionAdapter":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()

    def _rewrite_sql(self, sql_text: str) -> str:
        if self.engine == "postgres":
            return qmark_to_format(sql_text)
        return sql_text

    def execute(self, sql_text: str, params: Any = None) -> CursorAdapter:
        cursor = self._raw.execute(self._rewrite_sql(sql_text), normalize_params(params))
        return CursorAdapter(cursor)

    def executemany(self, sql_text: str, seq_of_params: Iterable[Sequence[Any]]) -> CursorAdapter:
        cursor = self._raw.executemany(
            self._rewrite_sql(sql_text),
            [normalize_params(item) for item in seq_of_params],
        )
        return CursorAdapter(cursor)

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def close(self) -> None:
        self._raw.close()

    def table_exists(self, table_name: str) -> bool:
        if self.engine == "postgres":
            row = self.execute(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = current_schema()
                  AND table_name = ?
                """,
                (table_name,),
            ).fetchone()
            return bool(row)

        row = self.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        return bool(row)

    def table_columns(self, table_name: str) -> tuple[str, ...]:
        if self.engine == "postgres":
            rows = self.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = ?
                ORDER BY ordinal_position
                """,
                (table_name,),
            ).fetchall()
            return tuple(str(row["column_name"]) for row in rows)

        rows = self.execute(f"PRAGMA table_info({quote_identifier(table_name)})").fetchall()
        return tuple(str(row[1]) for row in rows)

    def list_tables(self, prefix: str | None = None) -> list[str]:
        if self.engine == "postgres":
            sql_text = """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = current_schema()
            """
            params: list[Any] = []
            if prefix:
                sql_text += " AND table_name LIKE ?"
                params.append(f"{prefix}%")
            sql_text += " ORDER BY table_name"
            rows = self.execute(sql_text, params).fetchall()
            return [str(row["table_name"]) for row in rows]

        sql_text = """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
        """
        params: list[Any] = []
        if prefix:
            sql_text += " AND name LIKE ?"
            params.append(f"{prefix}%")
        sql_text += " ORDER BY name"
        rows = self.execute(sql_text, params).fetchall()
        return [str(row[0]) for row in rows]


def connect(target: str | Path | None = None) -> ConnectionAdapter:
    """创建数据库连接。"""
    resolved = resolve_database_target(target)
    engine = detect_database_engine(resolved)

    if engine == "postgres":
        raw = psycopg.connect(resolved, row_factory=dict_row)
        return ConnectionAdapter(raw, engine, resolved)

    db_path = Path(resolved)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    raw = sqlite3.connect(db_path)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys = ON")
    return ConnectionAdapter(raw, engine, str(db_path))
