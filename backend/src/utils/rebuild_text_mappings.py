"""
Rebuild PostgreSQL public.text_history_mappings from text-mode payload tables.

Rules:
1. Read all rows from public.mode_payload_tables where is_text = 1
2. Recreate public.text_history_mappings from scratch
3. Keep only id, mode_id, content, jiexi, title
4. Adapt to different source table structures by filling missing text columns with ''
5. Deduplicate inside the same mode_id by (mode_id, content, jiexi, title)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = BACKEND_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from db import auto_increment_primary_key  # pyright: ignore[reportMissingImports]
from db import connect, default_postgres_target  # pyright: ignore[reportMissingImports]
from database.yiyupotianji_seed_rows import (  # pyright: ignore[reportMissingImports]
    YIYUPOTIANJI_TEXT_POOL_CONTENTS,
)

def _get_default_db_path():
    try:
        return default_postgres_target()
    except RuntimeError:
        return ""
DEFAULT_DB_PATH = _get_default_db_path()
MAPPING_TABLE = "text_history_mappings"
TEXT_COLUMNS = ("content", "jiexi", "title")
MODE_244_ID = 244
MODE_244_TABLE = "mode_payload_244"

MODE_52_ID = 52

#: 四字玄机（mode 52）的备选文案池：49 组 (标题, 解肖)。
#: 标题是四字词，解肖是该期候选的 7 个生肖（命中判定 = 特肖落在解肖内）。
#: mode_payload_52 未被标记 is_text=1，通用重建路径会跳过它，
#: 因此在重建结束后单独回填，保证“重建不会丢掉这批候选”。
MODE_52_SIZIXUANJI_POOL: tuple[tuple[str, str], ...] = (
    ("否极泰来", "兔羊蛇牛猴鼠猪"),
    ("春风化雨", "马蛇牛龙鸡羊狗"),
    ("秋毫无犯", "羊龙狗鼠虎猪鸡"),
    ("雪中送炭", "狗鸡兔鼠虎龙猴"),
    ("锦上添花", "龙兔鸡马牛狗鼠"),
    ("月明星稀", "鼠鸡猪马狗牛虎"),
    ("水落石出", "鸡蛇鼠虎羊牛龙"),
    ("云淡风轻", "虎猪牛兔鼠羊鸡"),
    ("山高水长", "鸡猴牛鼠羊狗兔"),
    ("柳暗花明", "狗鼠龙牛兔马羊"),
    ("鹤立鸡群", "鸡猴牛鼠兔猪羊"),
    ("鱼跃龙门", "狗羊龙兔虎猪鸡"),
    ("马到成功", "猪虎牛鸡蛇兔马"),
    ("龙飞凤舞", "蛇鸡羊牛狗马鼠"),
    ("虎踞龙盘", "牛狗马羊鸡虎兔"),
    ("猴年马月", "马猴鸡兔猪龙牛"),
    ("守株待兔", "牛羊蛇狗虎鼠猴"),
    ("亡羊补牢", "鸡狗猪鼠龙兔猴"),
    ("对牛弹琴", "马猴狗猪羊蛇兔"),
    ("画蛇添足", "猴蛇龙马兔羊牛"),
    ("杯弓蛇影", "狗羊鼠马龙牛猪"),
    ("狐假虎威", "龙猪鼠羊兔蛇狗"),
    ("九牛一毛", "虎鸡马蛇猪牛猴"),
    ("万马奔腾", "猴狗蛇鼠兔马猪"),
    ("走马观花", "虎狗鼠鸡兔牛马"),
    ("青梅竹马", "鸡蛇猴马羊牛龙"),
    ("叶公好龙", "牛龙羊虎兔狗猪"),
    ("狼吞虎咽", "马猪鼠牛猴兔蛇"),
    ("猪朋狗友", "狗鸡马兔龙牛猴"),
    ("鸡鸣狗盗", "牛马狗龙羊鼠猪"),
    ("金鸡独立", "鸡鼠羊牛狗猪猴"),
    ("天马行空", "虎猴龙牛鸡猪狗"),
    ("老马识途", "猪蛇鸡羊猴龙马"),
    ("车水马龙", "龙虎猴蛇猪鼠兔"),
    ("杯水车薪", "羊鸡马蛇鼠猪牛"),
    ("雪泥鸿爪", "羊猴牛龙兔狗鼠"),
    ("雁过留声", "鸡牛兔猪羊蛇狗"),
    ("鸟语花香", "牛猴羊马猪蛇虎"),
    ("鱼目混珠", "龙蛇猪鼠鸡羊虎"),
    ("鹿死谁手", "鼠龙猪马羊鸡狗"),
    ("凤毛麟角", "鼠虎猴马兔狗牛"),
    ("龟年鹤寿", "猴羊虎鼠马蛇牛"),
    ("龙潭虎穴", "猴猪虎牛兔羊狗"),
    ("蛛丝马迹", "鸡蛇虎羊龙猪猴"),
    ("鸦雀无声", "蛇猴猪牛羊龙兔"),
    ("螳臂当车", "龙鸡虎蛇猪猴牛"),
    ("鹬蚌相争", "狗蛇马兔猴龙牛"),
    ("塞翁失马", "龙狗牛鼠兔马蛇"),
    ("闻鸡起舞", "猴龙兔鸡狗鼠猪"),
)


def quote_identifier(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def get_text_mode_tables(conn: Any) -> list[dict[str, Any]]:
    if not conn.table_exists("mode_payload_tables"):
        raise ValueError("Database does not contain mode_payload_tables")

    rows = conn.execute(
        """
        SELECT modes_id, title, table_name
        FROM mode_payload_tables
        WHERE COALESCE(is_text, 0) = 1
        ORDER BY CAST(modes_id AS INTEGER)
        """
    ).fetchall()
    return [
        {
            "modes_id": int(row["modes_id"]),
            "title": str(row["title"] or ""),
            "table_name": str(row["table_name"] or f"mode_payload_{row['modes_id']}"),
        }
        for row in rows
    ]


def rebuild_mapping_table(conn: Any) -> None:
    table_name = quote_identifier(MAPPING_TABLE)
    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    conn.execute(
        f"""
        CREATE TABLE {table_name} (
            {auto_increment_primary_key('id', conn.engine)},
            mode_id INTEGER NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            jiexi TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        f"""
        CREATE UNIQUE INDEX idx_text_history_unique
        ON {table_name} (mode_id, content, jiexi, title)
        """
    )
    conn.execute(
        f"""
        CREATE INDEX idx_text_history_mode_id
        ON {table_name} (mode_id)
        """
    )
    conn.commit()


def source_select_expr(columns: set[str], column_name: str) -> str:
    if column_name in columns:
        return f"COALESCE(CAST({quote_identifier(column_name)} AS TEXT), '')"
    return "''"


def insert_from_mode_table(conn: Any, modes_id: int, table_name: str) -> int:
    columns = set(conn.table_columns(table_name))
    if not any(column in columns for column in TEXT_COLUMNS):
        return 0

    where_parts = [
        f"{source_select_expr(columns, column)} != ''"
        for column in TEXT_COLUMNS
        if column in columns
    ]
    if not where_parts:
        return 0

    before_row = conn.execute(
        f"SELECT COUNT(*) AS cnt FROM {quote_identifier(MAPPING_TABLE)}"
    ).fetchone()
    before_count = int(before_row["cnt"] or 0) if before_row else 0

    conn.execute(
        f"""
        INSERT INTO {quote_identifier(MAPPING_TABLE)} (mode_id, content, jiexi, title)
        SELECT DISTINCT
            {modes_id} AS mode_id,
            {source_select_expr(columns, 'content')} AS content,
            {source_select_expr(columns, 'jiexi')} AS jiexi,
            {source_select_expr(columns, 'title')} AS title
        FROM {quote_identifier(table_name)}
        WHERE {" OR ".join(where_parts)}
        ON CONFLICT (mode_id, content, jiexi, title) DO NOTHING
        """
    )
    conn.commit()

    after_row = conn.execute(
        f"SELECT COUNT(*) AS cnt FROM {quote_identifier(MAPPING_TABLE)}"
    ).fetchone()
    after_count = int(after_row["cnt"] or 0) if after_row else 0
    return after_count - before_count


def insert_mode_244_content_pool(conn: Any) -> int:
    """Backfill mode_id=244 text mappings from source content and curated pool.

    mode_payload_244 currently stores only `content` rows and is not marked as
    `is_text=1` in mode_payload_tables, so the generic rebuild path skips it.
    We explicitly mirror its unique content into text_history_mappings and add a
    curated text pool to improve variety for the text-history formatter.
    """
    if not conn.table_exists(MODE_244_TABLE):
        return 0

    before_row = conn.execute(
        f"SELECT COUNT(*) AS cnt FROM {quote_identifier(MAPPING_TABLE)}"
    ).fetchone()
    before_count = int(before_row["cnt"] or 0) if before_row else 0

    conn.execute(
        f"""
        INSERT INTO {quote_identifier(MAPPING_TABLE)} (mode_id, content, jiexi, title)
        SELECT DISTINCT
            {MODE_244_ID} AS mode_id,
            COALESCE(CAST(content AS TEXT), '') AS content,
            '' AS jiexi,
            '' AS title
        FROM {quote_identifier(MODE_244_TABLE)}
        WHERE COALESCE(CAST(content AS TEXT), '') != ''
        ON CONFLICT (mode_id, content, jiexi, title) DO NOTHING
        """
    )

    for content in YIYUPOTIANJI_TEXT_POOL_CONTENTS:
        text = str(content or "").strip()
        if not text:
            continue
        conn.execute(
            f"""
            INSERT INTO {quote_identifier(MAPPING_TABLE)} (mode_id, content, jiexi, title)
            VALUES (?, ?, '', '')
            ON CONFLICT (mode_id, content, jiexi, title) DO NOTHING
            """,
            (MODE_244_ID, text),
        )
    conn.commit()

    after_row = conn.execute(
        f"SELECT COUNT(*) AS cnt FROM {quote_identifier(MAPPING_TABLE)}"
    ).fetchone()
    after_count = int(after_row["cnt"] or 0) if after_row else 0
    return after_count - before_count


def insert_mode_52_sizixuanji_pool(conn: Any) -> int:
    """回填 mode_id=52（四字玄机）的备选 (title, jiexi) 池。

    mode_payload_52 的 `title` 是四字词、`jiexi` 是候选 7 肖，两者必须配对；
    生成端与相邻期展示唯一性都会从 text_history_mappings 读取 mode 52 的候选，
    因此这里把 49 组备选写进映射表（幂等，重复执行不会重复插入）。
    """
    if not conn.table_exists(MAPPING_TABLE):
        raise ValueError(
            "text_history_mappings 不存在：请先执行完整重建（不带 --only-mode52）再回填 mode 52 池"
        )

    before_row = conn.execute(
        f"SELECT COUNT(*) AS cnt FROM {quote_identifier(MAPPING_TABLE)}"
    ).fetchone()
    before_count = int(before_row["cnt"] or 0) if before_row else 0

    for title, jiexi in MODE_52_SIZIXUANJI_POOL:
        conn.execute(
            f"""
            INSERT INTO {quote_identifier(MAPPING_TABLE)} (mode_id, content, jiexi, title)
            VALUES (?, '', ?, ?)
            ON CONFLICT (mode_id, content, jiexi, title) DO NOTHING
            """,
            (MODE_52_ID, jiexi, title),
        )
    conn.commit()

    after_row = conn.execute(
        f"SELECT COUNT(*) AS cnt FROM {quote_identifier(MAPPING_TABLE)}"
    ).fetchone()
    after_count = int(after_row["cnt"] or 0) if after_row else 0
    return after_count - before_count


def rebuild_text_history_mappings(db_path: str = DEFAULT_DB_PATH) -> dict[str, Any]:
    with connect(db_path) as conn:
        target_modes = get_text_mode_tables(conn)
        rebuild_mapping_table(conn)

        inserted = 0
        scanned_tables = 0
        missing_tables = 0
        skipped_without_text_columns = 0

        for mode in target_modes:
            modes_id = int(mode["modes_id"])
            table_name = str(mode["table_name"])

            if not conn.table_exists(table_name):
                missing_tables += 1
                print(f"[SKIP] modes_id={modes_id}: {table_name} does not exist")
                continue

            scanned_tables += 1
            columns = set(conn.table_columns(table_name))
            if not any(column in columns for column in TEXT_COLUMNS):
                skipped_without_text_columns += 1
                print(f"[SKIP] modes_id={modes_id}: {table_name} has no content/jiexi/title")
                continue

            delta = insert_from_mode_table(conn, modes_id, table_name)
            inserted += delta
            print(f"[OK] modes_id={modes_id}: inserted {delta} rows")

        mode_244_inserted = insert_mode_244_content_pool(conn)
        if mode_244_inserted > 0:
            print(f"[OK] modes_id=244: inserted {mode_244_inserted} rows from source+seed pool")

        mode_52_inserted = insert_mode_52_sizixuanji_pool(conn)
        if mode_52_inserted > 0:
            print(f"[OK] modes_id=52: inserted {mode_52_inserted} rows from seed pool")

        total_row = conn.execute(
            f"SELECT COUNT(*) AS cnt FROM {quote_identifier(MAPPING_TABLE)}"
        ).fetchone()
        total = int(total_row["cnt"] or 0) if total_row else 0

    return {
        "target_modes": len(target_modes),
        "scanned_tables": scanned_tables,
        "missing_tables": missing_tables,
        "skipped_without_text_columns": skipped_without_text_columns,
        "inserted": inserted + mode_244_inserted + mode_52_inserted,
        "mode_244_inserted": mode_244_inserted,
        "mode_52_inserted": mode_52_inserted,
        "total_after_dedup": total,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild public.text_history_mappings from public.mode_payload_tables where is_text=1."
    )
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="PostgreSQL DSN")
    parser.add_argument(
        "--only-mode52",
        action="store_true",
        help="只回填 mode 52（四字玄机）的 49 组备选 title/jiexi，不重建整张表",
    )
    args = parser.parse_args()

    if args.only_mode52:
        with connect(args.db_path) as conn:
            inserted = insert_mode_52_sizixuanji_pool(conn)
            total_row = conn.execute(
                f"SELECT COUNT(*) AS cnt FROM {quote_identifier(MAPPING_TABLE)} WHERE mode_id = ?",
                (MODE_52_ID,),
            ).fetchone()
            total = int(total_row["cnt"] or 0) if total_row else 0
        print(f"[OK] modes_id=52: inserted {inserted} rows; mode_id=52 现有 {total} 行")
        return

    print("=" * 60)
    print("Rebuild text_history_mappings")
    print(f"Database: {args.db_path}")
    print("Source: public.mode_payload_tables where is_text=1")
    print("=" * 60)
    result = rebuild_text_history_mappings(args.db_path)
    print(result)


if __name__ == "__main__":
    main()
