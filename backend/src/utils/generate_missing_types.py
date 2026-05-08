"""
为 mode_payload 表生成缺失的 type=1 (香港彩) 和 type=2 (澳门彩) 数据。

背景：
  外部 API 只提供了部分 modes_id 的 type=1/2 数据。
  对于缺失的，此脚本通过复制 type=3 (台湾彩) 记录并修改 type 来填充，
  确保前端切换游戏标签时每个模块都有数据可显示。

使用：
  python backend/src/utils/generate_missing_types.py
"""

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1]
UTILS_ROOT = SRC_ROOT / "utils"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(UTILS_ROOT) not in sys.path:
    sys.path.insert(0, str(UTILS_ROOT))

from db import connect, quote_identifier

DEFAULT_DB_PATH = "postgresql://postgres:2225427@localhost:5432/liuhecai"

# 旧模块关心的 modes_id 列表
LEGACY_MODES = [
    43, 197, 38, 246, 45, 50, 46, 8, 57, 63, 54, 151,
    12, 53, 51, 28, 31, 65, 68, 42, 34, 26, 58, 20, 52,
    59, 61, 3, 244, 48, 2, 49, 56, 108, 331, 62,
]


def get_column_list(conn, table_name: str) -> list[str]:
    """获取表的列名列表，排除 auto-increment id。"""
    cols = conn.execute(
        f"SELECT column_name FROM information_schema.columns "
        f"WHERE table_name = '{table_name}' "
        f"ORDER BY ordinal_position"
    ).fetchall()
    return [c["column_name"] for c in cols]


def generate_missing_types(db_path: str = DEFAULT_DB_PATH) -> dict[str, int]:
    """为缺少 type=1 或 type=2 数据的 mode_payload 表填充数据。"""
    results: dict[str, int] = {"type1_inserted": 0, "type2_inserted": 0}

    with connect(db_path) as conn:
        for modes_id in LEGACY_MODES:
            meta = conn.execute(
                "SELECT table_name FROM mode_payload_tables WHERE modes_id = ?",
                (modes_id,),
            ).fetchone()
            if not meta:
                continue

            tn = meta["table_name"]
            columns = get_column_list(conn, tn)

            # 检查已有的 type 分布
            type_rows = conn.execute(
                f"SELECT type, COUNT(*)::int as cnt FROM {quote_identifier(tn)} "
                f"GROUP BY type"
            ).fetchall()
            existing_types = {str(r["type"]): r["cnt"] for r in type_rows}
            has_type1 = "1" in existing_types
            has_type2 = "2" in existing_types

            # 获取 type=3 的记录用于复制
            type3_rows = conn.execute(
                f"SELECT * FROM {quote_identifier(tn)} WHERE type = 3"
            ).fetchall()

            if not type3_rows:
                continue

            quoted_tn = quote_identifier(tn)
            col_names = [c for c in columns if c != "id"]
            quoted_cols = [quote_identifier(c) for c in col_names]
            placeholders = ", ".join(["?"] * len(col_names))

            for target_type, has_data, label in [
                (1, has_type1, "type=1"),
                (2, has_type2, "type=2"),
            ]:
                if has_data:
                    continue

                insert_count = 0
                for row in type3_rows:
                    row_dict = dict(row)
                    vals = []
                    for c in col_names:
                        if c == "type":
                            vals.append(str(target_type))  # 用 TEXT 兼容 int/text 列
                        elif c == "source_record_id":
                            # 使用负值避免与原始 ID 冲突，且保持全数字以支持 CAST(... AS INTEGER)
                            original_id = str(row_dict.get(c, "0"))
                            try:
                                numeric_id = abs(int(float(original_id)))
                                vals.append(str(-numeric_id * 10 - target_type))
                            except (ValueError, TypeError):
                                vals.append(str(-hash(original_id) % 10_000_000))
                        elif c in ("res_code", "res_sx", "res_color"):
                            # 清空开奖结果，因为没有对应 type 的真实开奖数据
                            vals.append("")
                        else:
                            vals.append(row_dict.get(c))

                    try:
                        conn.execute(
                            f"INSERT INTO {quoted_tn} ({', '.join(quoted_cols)}) "
                            f"VALUES ({placeholders})",
                            vals,
                        )
                        insert_count += 1
                    except Exception:
                        # 主键冲突等错误跳过
                        pass

                if insert_count > 0:
                    conn.commit()
                    key = f"type{target_type}_inserted"
                    results[key] = results.get(key, 0) + insert_count
                    print(
                        f"modes_id={modes_id} ({tn}): 生成 {insert_count} 条 {label} 数据"
                    )

    return results


def main():
    db_path = DEFAULT_DB_PATH
    print(f"=== 开始生成缺失的 type=1/2 数据 (db={db_path}) ===\n")

    results = generate_missing_types(db_path)

    print(f"\n=== 生成完成 ===")
    print(f"  type=1 (香港彩): 生成 {results.get('type1_inserted', 0)} 条")
    print(f"  type=2 (澳门彩): 生成 {results.get('type2_inserted', 0)} 条")
    print(f"  总计: {results.get('type1_inserted', 0) + results.get('type2_inserted', 0)} 条")


if __name__ == "__main__":
    main()
