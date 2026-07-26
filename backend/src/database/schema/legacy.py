"""legacy image and compatibility schema helpers."""

from __future__ import annotations

from typing import Any, Iterable

from database.migrations import add_column_if_missing


def ensure_legacy_asset_tables(conn: Any, pk_sql: str) -> None:
    """Create/update the legacy image asset table."""
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS legacy_image_assets (
            {pk_sql},
            source_key TEXT NOT NULL DEFAULT 'legacy-post-list',
            source_pc INTEGER,
            source_web INTEGER,
            source_type INTEGER,
            title TEXT,
            file_name TEXT NOT NULL UNIQUE,
            storage_path TEXT NOT NULL,
            legacy_upload_path TEXT NOT NULL UNIQUE,
            cover_image TEXT NOT NULL UNIQUE,
            mime_type TEXT NOT NULL,
            file_size INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0,
            enabled INTEGER NOT NULL DEFAULT 1,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    add_column_if_missing(
        conn, "legacy_image_assets", "source_key",
        "TEXT NOT NULL DEFAULT 'legacy-post-list'",
    )
    add_column_if_missing(conn, "legacy_image_assets", "source_pc", "INTEGER")
    add_column_if_missing(conn, "legacy_image_assets", "source_web", "INTEGER")
    add_column_if_missing(conn, "legacy_image_assets", "source_type", "INTEGER")
    add_column_if_missing(conn, "legacy_image_assets", "title", "TEXT")
    add_column_if_missing(conn, "legacy_image_assets", "storage_path", "TEXT")
    add_column_if_missing(conn, "legacy_image_assets", "legacy_upload_path", "TEXT")
    add_column_if_missing(conn, "legacy_image_assets", "cover_image", "TEXT")
    add_column_if_missing(conn, "legacy_image_assets", "mime_type", "TEXT")
    add_column_if_missing(
        conn, "legacy_image_assets", "file_size", "INTEGER NOT NULL DEFAULT 0",
    )
    add_column_if_missing(
        conn, "legacy_image_assets", "sort_order", "INTEGER NOT NULL DEFAULT 0",
    )
    add_column_if_missing(
        conn, "legacy_image_assets", "enabled", "INTEGER NOT NULL DEFAULT 1",
    )
    add_column_if_missing(conn, "legacy_image_assets", "notes", "TEXT")


def ensure_liubuzhong_table(conn: Any, pk_sql: str) -> None:
    """Create/update the special liubuzhong payload table (modes_id=333)."""
    modes_id = 333
    table_name = f"mode_payload_{modes_id}"

    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {pk_sql},
            term TEXT NOT NULL,
            year TEXT,
            type INTEGER DEFAULT 3,
            web_id INTEGER DEFAULT 6,
            res_code TEXT DEFAULT '',
            res_sx TEXT DEFAULT '',
            u6_code TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    engine = getattr(conn, "engine", "sqlite")
    if engine == "postgres":
        row = conn.execute("SELECT NOW() AS now").fetchone()
        now = str(row["now"]) if row else ""
    else:
        row = conn.execute("SELECT datetime('now') AS now").fetchone()
        now = str(row["now"]) if row else ""

    if conn.table_exists("mode_payload_tables"):
        metadata_columns = set(conn.table_columns("mode_payload_tables"))
        lookup_sql = "SELECT modes_id FROM mode_payload_tables WHERE modes_id = ?"
        existing = conn.execute(lookup_sql, (modes_id,)).fetchone()
        if not existing:
            insert_columns = ["modes_id", "title", "table_name", "record_count", "created_at"]
            insert_values: list[Any] = [modes_id, "???", table_name, 0, now]

            if "filename" in metadata_columns:
                insert_columns.insert(2, "filename")
                insert_values.insert(2, f"{modes_id}.json")
            if "is_image" in metadata_columns:
                insert_columns.append("is_image")
                insert_values.append(0)
            if "is_text" in metadata_columns:
                insert_columns.append("is_text")
                insert_values.append(0)
            if "updated_at" in metadata_columns:
                insert_columns.append("updated_at")
                insert_values.append(now)

            placeholders = ", ".join(["?"] * len(insert_values))
            conn.execute(
                f"""
                INSERT INTO mode_payload_tables ({", ".join(insert_columns)})
                VALUES ({placeholders})
                """,
                tuple(insert_values),
            )

    add_column_if_missing(conn, table_name, "u6_code", "TEXT NOT NULL DEFAULT ''")


def _current_db_now(conn: Any) -> str:
    engine = getattr(conn, "engine", "sqlite")
    if engine == "postgres":
        row = conn.execute("SELECT NOW() AS now").fetchone()
        return str(row["now"]) if row else ""
    row = conn.execute("SELECT datetime('now') AS now").fetchone()
    return str(row["now"]) if row else ""


def _ensure_mode_payload_metadata(
    conn: Any,
    *,
    modes_id: int,
    title: str,
    table_name: str,
    now: str,
    is_image: int = 0,
    is_text: int = 0,
) -> None:
    if not conn.table_exists("mode_payload_tables"):
        return

    metadata_columns = set(conn.table_columns("mode_payload_tables"))
    existing = conn.execute(
        "SELECT modes_id FROM mode_payload_tables WHERE modes_id = ?",
        (modes_id,),
    ).fetchone()
    if existing:
        return

    insert_columns = ["modes_id", "title", "table_name", "record_count", "created_at"]
    insert_values: list[Any] = [modes_id, title, table_name, 0, now]

    if "filename" in metadata_columns:
        insert_columns.insert(2, "filename")
        insert_values.insert(2, f"{modes_id}.json")
    if "is_image" in metadata_columns:
        insert_columns.append("is_image")
        insert_values.append(int(is_image))
    if "is_text" in metadata_columns:
        insert_columns.append("is_text")
        insert_values.append(int(is_text))
    if "updated_at" in metadata_columns:
        insert_columns.append("updated_at")
        insert_values.append(now)

    placeholders = ", ".join(["?"] * len(insert_values))
    conn.execute(
        f"""
        INSERT INTO mode_payload_tables ({", ".join(insert_columns)})
        VALUES ({placeholders})
        """,
        tuple(insert_values),
    )


def ensure_basic_prediction_payload_table(
    conn: Any,
    pk_sql: str,
    *,
    modes_id: int,
    title: str,
) -> None:
    """Create/update a simple content-based prediction payload table.

    This mirrors the common legacy shape used by zodiac/head prediction modules so
    new site-specific mechanisms can be added without touching the core
    generation pipeline.
    """
    table_name = f"mode_payload_{modes_id}"
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {pk_sql},
            web TEXT,
            type TEXT,
            year TEXT,
            term TEXT,
            res_code TEXT,
            res_sx TEXT,
            res_color TEXT,
            status INTEGER,
            content TEXT,
            web_id INTEGER,
            modes_id INTEGER,
            source_record_id TEXT,
            fetched_at TEXT
        )
        """
    )

    add_column_if_missing(conn, table_name, "web", "TEXT")
    add_column_if_missing(conn, table_name, "type", "TEXT")
    add_column_if_missing(conn, table_name, "year", "TEXT")
    add_column_if_missing(conn, table_name, "term", "TEXT")
    add_column_if_missing(conn, table_name, "res_code", "TEXT")
    add_column_if_missing(conn, table_name, "res_sx", "TEXT")
    add_column_if_missing(conn, table_name, "res_color", "TEXT")
    add_column_if_missing(conn, table_name, "status", "INTEGER")
    add_column_if_missing(conn, table_name, "content", "TEXT")
    add_column_if_missing(conn, table_name, "web_id", "INTEGER")
    add_column_if_missing(conn, table_name, "modes_id", "INTEGER")
    add_column_if_missing(conn, table_name, "source_record_id", "TEXT")
    add_column_if_missing(conn, table_name, "fetched_at", "TEXT")

    _ensure_mode_payload_metadata(
        conn,
        modes_id=modes_id,
        title=title,
        table_name=table_name,
        now=_current_db_now(conn),
    )


def ensure_image_prediction_payload_table(
    conn: Any,
    pk_sql: str,
    *,
    modes_id: int,
    title: str,
) -> None:
    """Create/update a site-only image prediction payload table with image_url."""
    table_name = f"mode_payload_{modes_id}"
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {pk_sql},
            web TEXT,
            type TEXT,
            year TEXT,
            term TEXT,
            res_code TEXT,
            res_sx TEXT,
            res_color TEXT,
            status INTEGER,
            title TEXT,
            content TEXT,
            image_url TEXT,
            web_id INTEGER,
            modes_id INTEGER,
            source_record_id TEXT,
            fetched_at TEXT
        )
        """
    )

    add_column_if_missing(conn, table_name, "web", "TEXT")
    add_column_if_missing(conn, table_name, "type", "TEXT")
    add_column_if_missing(conn, table_name, "year", "TEXT")
    add_column_if_missing(conn, table_name, "term", "TEXT")
    add_column_if_missing(conn, table_name, "res_code", "TEXT")
    add_column_if_missing(conn, table_name, "res_sx", "TEXT")
    add_column_if_missing(conn, table_name, "res_color", "TEXT")
    add_column_if_missing(conn, table_name, "status", "INTEGER")
    add_column_if_missing(conn, table_name, "title", "TEXT")
    add_column_if_missing(conn, table_name, "content", "TEXT")
    add_column_if_missing(conn, table_name, "image_url", "TEXT")
    add_column_if_missing(conn, table_name, "web_id", "INTEGER")
    add_column_if_missing(conn, table_name, "modes_id", "INTEGER")
    add_column_if_missing(conn, table_name, "source_record_id", "TEXT")
    add_column_if_missing(conn, table_name, "fetched_at", "TEXT")

    _ensure_mode_payload_metadata(
        conn,
        modes_id=modes_id,
        title=title,
        table_name=table_name,
        now=_current_db_now(conn),
        is_image=1,
        is_text=0,
    )


def ensure_xiao_code_prediction_payload_table(
    conn: Any,
    pk_sql: str,
    *,
    modes_id: int,
    title: str,
) -> None:
    """Create/update a payload table with xiao/code columns."""
    table_name = f"mode_payload_{modes_id}"
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {pk_sql},
            web TEXT,
            type TEXT,
            year TEXT,
            term TEXT,
            res_code TEXT,
            res_sx TEXT,
            res_color TEXT,
            status INTEGER,
            content TEXT,
            xiao TEXT,
            code TEXT,
            web_id INTEGER,
            modes_id INTEGER,
            source_record_id TEXT,
            fetched_at TEXT
        )
        """
    )

    add_column_if_missing(conn, table_name, "web", "TEXT")
    add_column_if_missing(conn, table_name, "type", "TEXT")
    add_column_if_missing(conn, table_name, "year", "TEXT")
    add_column_if_missing(conn, table_name, "term", "TEXT")
    add_column_if_missing(conn, table_name, "res_code", "TEXT")
    add_column_if_missing(conn, table_name, "res_sx", "TEXT")
    add_column_if_missing(conn, table_name, "res_color", "TEXT")
    add_column_if_missing(conn, table_name, "status", "INTEGER")
    add_column_if_missing(conn, table_name, "content", "TEXT")
    add_column_if_missing(conn, table_name, "xiao", "TEXT")
    add_column_if_missing(conn, table_name, "code", "TEXT")
    add_column_if_missing(conn, table_name, "web_id", "INTEGER")
    add_column_if_missing(conn, table_name, "modes_id", "INTEGER")
    add_column_if_missing(conn, table_name, "source_record_id", "TEXT")
    add_column_if_missing(conn, table_name, "fetched_at", "TEXT")

    _ensure_mode_payload_metadata(
        conn,
        modes_id=modes_id,
        title=title,
        table_name=table_name,
        now=_current_db_now(conn),
    )


def ensure_image_prediction_created_table(
    conn: Any,
    *,
    modes_id: int,
) -> None:
    """Ensure PostgreSQL created.mode_payload_{mode_id} also exposes image_url."""
    if getattr(conn, "engine", "") != "postgres":
        return
    table_name = f"mode_payload_{int(modes_id)}"
    conn.execute("CREATE SCHEMA IF NOT EXISTS created")
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS created.{table_name} (
            id TEXT,
            web TEXT,
            type TEXT,
            year TEXT,
            term TEXT,
            res_code TEXT,
            res_sx TEXT,
            res_color TEXT,
            status INTEGER,
            title TEXT,
            content TEXT,
            image_url TEXT,
            web_id INTEGER,
            modes_id INTEGER,
            source_record_id TEXT,
            fetched_at TEXT,
            created_at TEXT,
            mode_id INTEGER
        )
        """
    )
    conn.execute(
        f"""
        ALTER TABLE created.{table_name}
        ADD COLUMN IF NOT EXISTS image_url TEXT
        """
    )


def ensure_brain_teaser_prediction_created_table(conn: Any) -> None:
    """Ensure PostgreSQL created.mode_payload_475 also exposes image_url."""
    if getattr(conn, "engine", "") != "postgres":
        return
    conn.execute("CREATE SCHEMA IF NOT EXISTS created")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS created.mode_payload_475 (
            id TEXT,
            web TEXT,
            type TEXT,
            year TEXT,
            term TEXT,
            res_code TEXT,
            res_sx TEXT,
            res_color TEXT,
            status INTEGER,
            title TEXT,
            content TEXT,
            image_url TEXT,
            answer TEXT,
            tips TEXT,
            jiexi TEXT,
            web_id INTEGER,
            modes_id INTEGER,
            source_record_id TEXT,
            fetched_at TEXT,
            created_at TEXT,
            mode_id INTEGER
        )
        """
    )
    conn.execute(
        """
        ALTER TABLE created.mode_payload_475
        ADD COLUMN IF NOT EXISTS image_url TEXT
        """
    )


def ensure_brain_teaser_prediction_payload_table(
    conn: Any,
    pk_sql: str,
    *,
    modes_id: int = 475,
    title: str = "脑筋急转弯",
) -> None:
    """Create/update the dedicated payload table for brain teaser predictions."""
    table_name = f"mode_payload_{modes_id}"
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {pk_sql},
            web TEXT,
            type TEXT,
            year TEXT,
            term TEXT,
            res_code TEXT,
            res_sx TEXT,
            res_color TEXT,
            status INTEGER,
            title TEXT,
            content TEXT,
            image_url TEXT,
            answer TEXT,
            tips TEXT,
            jiexi TEXT,
            web_id INTEGER,
            modes_id INTEGER,
            source_record_id TEXT,
            fetched_at TEXT
        )
        """
    )

    add_column_if_missing(conn, table_name, "web", "TEXT")
    add_column_if_missing(conn, table_name, "type", "TEXT")
    add_column_if_missing(conn, table_name, "year", "TEXT")
    add_column_if_missing(conn, table_name, "term", "TEXT")
    add_column_if_missing(conn, table_name, "res_code", "TEXT")
    add_column_if_missing(conn, table_name, "res_sx", "TEXT")
    add_column_if_missing(conn, table_name, "res_color", "TEXT")
    add_column_if_missing(conn, table_name, "status", "INTEGER")
    add_column_if_missing(conn, table_name, "title", "TEXT")
    add_column_if_missing(conn, table_name, "content", "TEXT")
    add_column_if_missing(conn, table_name, "image_url", "TEXT")
    add_column_if_missing(conn, table_name, "answer", "TEXT")
    add_column_if_missing(conn, table_name, "tips", "TEXT")
    add_column_if_missing(conn, table_name, "jiexi", "TEXT")
    add_column_if_missing(conn, table_name, "web_id", "INTEGER")
    add_column_if_missing(conn, table_name, "modes_id", "INTEGER")
    add_column_if_missing(conn, table_name, "source_record_id", "TEXT")
    add_column_if_missing(conn, table_name, "fetched_at", "TEXT")

    _ensure_mode_payload_metadata(
        conn,
        modes_id=modes_id,
        title=title,
        table_name=table_name,
        now=_current_db_now(conn),
    )


def ensure_site_specific_prediction_tables(conn: Any, pk_sql: str) -> None:
    """Bootstrap isolated payload tables for site-only prediction modules."""
    definitions: Iterable[tuple[int, str]] = (
        (77, "14码中特"),
        (78, "四肖四码"),
        (81, "15码中特"),
        (117, "三肖四尾"),
        (123, "四尾八码"),
        (470, "平特3肖"),
        (471, "两头中特"),
        (472, "绝杀1肖"),
        (473, "绝杀2肖"),
        (485, "内幕5不中"),
    )
    for modes_id, title in definitions:
        ensure_basic_prediction_payload_table(
            conn,
            pk_sql,
            modes_id=modes_id,
            title=title,
        )
    for modes_id, title in (
        (72, "三肖15码中特"),
        (219, "前后特肖"),
    ):
        ensure_xiao_code_prediction_payload_table(
            conn,
            pk_sql,
            modes_id=modes_id,
            title=title,
        )
    ensure_image_prediction_payload_table(
        conn,
        pk_sql,
        modes_id=474,
        title="四不像中特图",
    )
    ensure_image_prediction_created_table(conn, modes_id=474)
    ensure_image_prediction_payload_table(
        conn,
        pk_sql,
        modes_id=476,
        title="跑马图解（带图）",
    )
    ensure_image_prediction_created_table(conn, modes_id=476)
    ensure_image_prediction_payload_table(
        conn,
        pk_sql,
        modes_id=478,
        title="台湾跑马图（带图）",
    )
    ensure_image_prediction_created_table(conn, modes_id=478)
    ensure_brain_teaser_prediction_payload_table(conn, pk_sql)
    ensure_brain_teaser_prediction_created_table(conn)


def ensure_twcaibawang_prediction_tables(conn: Any, pk_sql: str) -> None:
    """Bootstrap twcaibawang-only prediction payload tables."""
    for modes_id, title in (
        (479, "四段中特"),
        (480, "凶吉六肖"),
        (481, "稳杀10码"),
        (482, "四行中特"),
        (483, "四头中特"),
    ):
        ensure_basic_prediction_payload_table(
            conn,
            pk_sql,
            modes_id=modes_id,
            title=title,
        )

    ensure_xiao_code_prediction_payload_table(
        conn,
        pk_sql,
        modes_id=484,
        title="六肖十八码",
    )
