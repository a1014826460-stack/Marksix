"""
将固定数据 JSON 文件导入到数据库的 fixed_data 表。

支持两种模式：
    - 重建模式（默认）：删除旧表并重新创建，导入全部数据
    - 追加模式（--append）：保留已有数据，只追加新行，自动补充新增列

用法：
    # 重建（清空旧数据）
    python backend/src/utils/import_fixed_data.py

    # 追加（保留已有数据，不更改原有内容）
    python backend/src/utils/import_fixed_data.py --append

    # 指定 JSON 文件和数据库
    python backend/src/utils/import_fixed_data.py --fixed-data-path path/to/data.json --db-path "postgresql://..."
"""

import argparse
import json
from pathlib import Path
from typing import Any

from db import connect, default_postgres_target


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXED_DATA_PATH = BACKEND_ROOT / "data" / "fixed_data.json"
def _get_default_db_target():
    try:
        return default_postgres_target()
    except RuntimeError:
        return ""
DEFAULT_DB_TARGET = _get_default_db_target()
FIXED_TABLE_NAME = "fixed_data"


def quote_identifier(identifier: str) -> str:
    """用双引号包裹数据库标识符（表名/列名），防止关键字冲突和 SQL 注入。"""
    return '"' + identifier.replace('"', '""') + '"'


def load_fixed_data(path: str | Path) -> dict[str, Any]:
    """从 JSON 文件加载固定数据。

    期望格式：{"data": [{"col1": val1, ...}, ...]}
    顶层必须是包含 "data" 键的 dict，"data" 必须是对象列表。

    Returns:
        解析后的完整 JSON 数据 dict。
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("data"), list):
        raise ValueError("fixed_data.json must contain a top-level data list.")
    if not all(isinstance(row, dict) for row in data["data"]):
        raise ValueError("fixed_data.json data must be a list of objects.")
    return data


def infer_sql_type(values: list[Any]) -> str:
    """根据列的实际值推断 SQL 类型。

    遍历列表中的非空值，按优先级判断：
        - 全为 bool            → INTEGER (SQLite 无 BOOLEAN)
        - 全为 int (非 bool)   → INTEGER
        - 全为 int 或 float     → REAL
        - 其他情况             → TEXT

    Returns:
        "INTEGER" / "REAL" / "TEXT"。
    """
    # 过滤掉 None 和空字符串，只分析有效值的类型
    non_empty_values = [value for value in values if value is not None and value != ""]
    if not non_empty_values:
        return "TEXT"
    if all(isinstance(value, bool) for value in non_empty_values):
        return "INTEGER"
    if all(isinstance(value, int) and not isinstance(value, bool) for value in non_empty_values):
        return "INTEGER"
    if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in non_empty_values):
        return "REAL"
    return "TEXT"


def payload_value_to_sql(value: Any) -> Any:
    """将 JSON 中的 Python 值转换为可写入 SQL 的值。

    - dict / list → JSON 字符串（ensure_ascii=False 保留中文）
    - bool        → 0/1（SQLite/PostgreSQL 通用整数布尔）
    - 其他类型     → 原值返回
    """
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return int(value)
    return value


def data_columns(rows: list[dict[str, Any]]) -> list[str]:
    """从数据行列表中提取所有不重复的列名，保持首次出现的顺序。

    遍历每行的 key，按首次出现顺序收集去重后的列名列表。
    这确保了即使不同行的字段不完全一致，也能覆盖所有列。
    """
    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                columns.append(str(key))
    return columns


def drop_old_fixed_tables(conn: Any) -> None:
    """删除数据库中所有以 fixed_ 开头的旧表。

    重建模式下使用，确保每次导入从干净状态开始。
    遍历 conn.list_tables() 查找所有匹配表名并逐一 DROP。
    """
    for table_name in conn.list_tables():
        if table_name == FIXED_TABLE_NAME or table_name.startswith("fixed_"):
            conn.execute(f"DROP TABLE IF EXISTS {quote_identifier(table_name)}")


def create_fixed_data_table(conn: Any, rows: list[dict[str, Any]]) -> list[str]:
    """根据数据行创建 fixed_data 表。

    1. 从数据中提取所有列名（data_columns）
    2. 对每列调用 infer_sql_type 推断类型
    3. 执行 CREATE TABLE
    4. 为 id / sign / (sign, name) 建立索引以加速查询

    Returns:
        创建的表所包含的列名列表（保持顺序）。
    """
    columns = data_columns(rows)
    if not columns:
        raise ValueError("fixed_data.json data is empty; cannot create fixed_data columns.")

    # 生成列定义，如 "id" INTEGER, "name" TEXT, ...
    definitions = [
        f"{quote_identifier(column)} {infer_sql_type([row.get(column) for row in rows])}"
        for column in columns
    ]
    conn.execute(
        f"""
        CREATE TABLE {quote_identifier(FIXED_TABLE_NAME)} (
            {", ".join(definitions)}
        )
        """
    )

    # 建立常用查询索引
    if "id" in columns:
        conn.execute(
            f"CREATE INDEX idx_fixed_data_id ON {quote_identifier(FIXED_TABLE_NAME)} ({quote_identifier('id')})"
        )
    if "sign" in columns:
        conn.execute(
            f"CREATE INDEX idx_fixed_data_sign ON {quote_identifier(FIXED_TABLE_NAME)} ({quote_identifier('sign')})"
        )
    if "sign" in columns and "name" in columns:
        conn.execute(
            f"""
            CREATE INDEX idx_fixed_data_sign_name
            ON {quote_identifier(FIXED_TABLE_NAME)} ({quote_identifier('sign')}, {quote_identifier('name')})
            """
        )

    return columns


def insert_fixed_data_rows(
    conn: Any,
    columns: list[str],
    rows: list[dict[str, Any]],
) -> None:
    """向 fixed_data 表批量插入数据行。

    使用 executemany 一次性插入所有行，每条记录的每个字段
    都经过 payload_value_to_sql 转换为数据库兼容格式。

    Args:
        conn: 数据库连接。
        columns: 目标表的列名列表（顺序需与 INSERT 语句一致）。
        rows: 待插入的数据行列表。
    """
    placeholders = ", ".join(["?"] * len(columns))
    insert_sql = (
        f"INSERT INTO {quote_identifier(FIXED_TABLE_NAME)} "
        f"({', '.join(quote_identifier(column) for column in columns)}) "
        f"VALUES ({placeholders})"
    )
    conn.executemany(
        insert_sql,
        [[payload_value_to_sql(row.get(column)) for column in columns] for row in rows],
    )


def ensure_columns_match(conn: Any, rows: list[dict[str, Any]]) -> list[str]:
    """追加模式下：确保表存在，并补齐缺失的列。

    1. 如果表不存在 → 调用 create_fixed_data_table 创建
    2. 如果表已存在 → 对比数据列与表列，用 ALTER TABLE ADD COLUMN 补齐缺失列
    3. 返回完整的列名列表（保持与数据一致的顺序）

    这样可以在不删除旧数据的前提下支持新增字段。
    """
    new_columns = data_columns(rows)

    if not conn.table_exists(FIXED_TABLE_NAME):
        return create_fixed_data_table(conn, rows)

    # 表已存在，检查并添加缺失的列
    existing_cols = set(conn.table_columns(FIXED_TABLE_NAME))
    for col in new_columns:
        if col not in existing_cols:
            col_type = infer_sql_type([row.get(col) for row in rows])
            conn.execute(
                f"ALTER TABLE {quote_identifier(FIXED_TABLE_NAME)} "
                f"ADD COLUMN {quote_identifier(col)} {col_type}"
            )
            print(f"  [追加列] {col} ({col_type})")

    return new_columns


def import_fixed_data(
    fixed_data_path: str | Path = DEFAULT_FIXED_DATA_PATH,
    db_path: str | Path = DEFAULT_DB_TARGET,
    append: bool = False,
) -> None:
    """将 fixed_data JSON 文件导入数据库。

    流程：
        - 重建模式 (append=False)：
            1. 删除所有 fixed_* 旧表
            2. 根据 JSON 数据自动推断列和类型创建新表
            3. 批量插入数据
        - 追加模式 (append=True)：
            1. 如果表不存在则创建，存在则补齐缺失列
            2. 只插入新数据，不删除不修改已有行

    Args:
        fixed_data_path: JSON 数据文件路径。
        db_path: 数据库目标路径或 DSN。
        append: True 为追加模式，False 为重建模式。
    """
    fixed_data_path = Path(fixed_data_path)
    data = load_fixed_data(fixed_data_path)
    rows = data["data"]

    with connect(db_path) as conn:
        if append:
            # 追加模式：保留已有数据，只添加新列和新行
            columns = ensure_columns_match(conn, rows)
        else:
            # 重建模式：清空旧表后全新导入
            drop_old_fixed_tables(conn)
            columns = create_fixed_data_table(conn, rows)

        insert_fixed_data_rows(conn, columns, rows)

    mode_text = "追加" if append else "重建"
    print(f"导入完成 ({mode_text}模式)")
    print(f"  行数: {len(rows)}")
    print(f"  列数: {len(columns)}")
    print(f"  列名: {', '.join(columns)}")
    print(f"  数据库: {db_path}")


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="将 fixed_data JSON 导入数据库。默认清空重建，--append 追加。"
    )
    parser.add_argument(
        "--fixed-data-path",
        default=str(DEFAULT_FIXED_DATA_PATH),
        help="JSON 数据文件路径。",
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_TARGET),
        help="数据库目标。默认使用 PostgreSQL；如需 SQLite，请显式传入 SQLite 路径。",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        default=False,
        help="追加模式：保留已有数据，只添加新行（默认：清空重建）。",
    )
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    import_fixed_data(args.fixed_data_path, args.db_path, append=args.append)
