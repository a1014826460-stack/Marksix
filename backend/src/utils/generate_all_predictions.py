"""
批量预测数据生成脚本 v4 — 全模块覆盖
============================================================
对所有 PREDICTION_CONFIGS 中的 337 个模块，为香港彩(type=1)和
澳门彩(type=2)的全部开奖期数生成预测数据。

核心逻辑：
  1. 遍历所有 lottery_draws (type=1, type=2)
  2. 对每个模块 × 每期 draw，调用 predict() 生成预测内容
  3. UPSERT: 先 DELETE 已有行 (type + year + term + web=4)，再 INSERT
  4. 只生成 web=4 的数据

用法：python -X utf8 backend/src/utils/generate_all_predictions.py
      python -X utf8 backend/src/utils/generate_all_predictions.py --dry-run
      python -X utf8 backend/src/utils/generate_all_predictions.py --mechanism title_234
"""

import argparse
import json
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = BACKEND_ROOT / "src"
PREDICT_ROOT = SRC_ROOT / "predict"
for p in (PREDICT_ROOT, SRC_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from mechanisms import PREDICTION_CONFIGS
from utils.created_prediction_store import upsert_created_prediction_row

DB_DSN = "postgresql://postgres:2225427@localhost:5432/liuhecai"

# ── 数据库连接 ───────────────────────────────────────────
def get_db_conn():
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(DB_DSN, row_factory=dict_row)


# ── 读取全部有效开奖数据 ─────────────────────────────────
def get_all_draws(conn, lottery_type_id):
    """读取该彩种的所有有效开奖记录（按 year/term 降序）"""
    cur = conn.execute(
        """SELECT year, term, numbers FROM lottery_draws
           WHERE lottery_type_id = %s AND numbers IS NOT NULL AND numbers != ''
           ORDER BY year DESC, term DESC""",
        (lottery_type_id,))
    draws = []
    for r in cur.fetchall():
        nums = [n.strip() for n in r["numbers"].split(",") if n.strip()]
        try:
            ints = [int(n) for n in nums]
            if any(n < 1 or n > 49 for n in ints):
                continue
            processed = [str(n).zfill(2) for n in ints]
            draws.append({
                "year": int(r["year"]),
                "term": int(r["term"]),
                "numbers": processed,
                "numbers_str": ",".join(processed),
            })
        except ValueError:
            continue
    return draws


# ── 表结构缓存 ───────────────────────────────────────────
_table_schema_cache = {}

def get_table_columns(conn, table_name):
    if table_name not in _table_schema_cache:
        cur = conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=%s", (table_name,))
        _table_schema_cache[table_name] = {r["column_name"] for r in cur.fetchall()}
    return _table_schema_cache[table_name]


# ── 生肖 / 映射加载 ─────────────────────────────────────
def load_fixed_data_map(conn, sign_name):
    """从 fixed_data 表加载 标签→值列表 映射（psycopg 直连版本）"""
    cur = conn.execute(
        "SELECT name, code FROM fixed_data WHERE sign = %s ORDER BY id",
        (sign_name,))
    result = {}
    for r in cur.fetchall():
        codes = [c.strip() for c in (r["code"] or "").split(",") if c.strip()]
        if codes:
            result[r["name"]] = tuple(codes)
    return result


def number_to_zodiac(zodiac_map, num):
    num_str = str(num).zfill(2)
    for z, codes in zodiac_map.items():
        if num_str in codes:
            return z
    return ""


# ── 解析 predict() 返回值 ─────────────────────────────────
def parse_prediction_result(result, draw, zodiac_map, mode_id):
    """解析 predict() 返回的 result dict，构建插入用的行数据"""
    if not result or "prediction" not in result:
        return None

    pred = result["prediction"]
    raw_content = pred.get("content", "")

    nums = draw["numbers"]
    all_zodiacs = [number_to_zodiac(zodiac_map, n) for n in nums
                   if number_to_zodiac(zodiac_map, n)]
    res_sx = ",".join(dict.fromkeys(z for z in all_zodiacs if z))

    # 基础字段
    row = {
        "year": str(draw["year"]),
        "term": str(draw["term"]),
        "res_code": draw["numbers_str"],
        "res_sx": res_sx,
        "table_modes_id": mode_id,
    }

    # 解析 content 字段
    if isinstance(raw_content, dict):
        # 黑白无双: {"hei": "...", "bai": "..."}
        if "hei" in raw_content and "bai" in raw_content:
            row["hei"] = raw_content["hei"]
            row["bai"] = raw_content["bai"]
            row["content"] = ""
        # {"title": "...", "jiexi": "..."}
        elif "title" in raw_content:
            row["title"] = raw_content.get("title", "")
            row["jiexi"] = raw_content.get("jiexi", "")
            row["content"] = ""
        # 三期中特: {"start":"","end":"","content":[...]}
        elif "content" in raw_content and isinstance(raw_content["content"], list):
            row["start"] = str(raw_content.get("start", "") or "")
            row["end"] = str(raw_content.get("end", "") or "")
            row["content"] = json.dumps(raw_content["content"], ensure_ascii=False)
        else:
            row["content"] = json.dumps(raw_content, ensure_ascii=False)
    elif isinstance(raw_content, list):
        row["content"] = json.dumps(raw_content, ensure_ascii=False)
    else:
        row["content"] = str(raw_content) if raw_content else ""

    return row


# ── UPSERT 写入 ──────────────────────────────────────────
def upsert_row(conn, table_name, row_data, game_type):
    """将预测结果写入 created schema，并按期次执行更新或插入。"""
    cols = get_table_columns(conn, table_name)
    content_val = row_data.get("content", "")
    mode_id = row_data["table_modes_id"]

    # 构建写入数据；真正的目标表结构由 created schema 同名表自动同步。
    data = {
        "year": row_data["year"],
        "term": row_data["term"],
        "res_code": row_data["res_code"],
        "res_sx": row_data["res_sx"],
    }

    # 类型列
    if "type" in cols:
        data["type"] = int(game_type)
    if "web" in cols:
        data["web"] = 4
    if "web_id" in cols:
        data["web_id"] = 4
    if "modes_id" in cols:
        data["modes_id"] = mode_id
    if "status" in cols:
        data["status"] = 1
    if "res_color" in cols:
        data["res_color"] = row_data.get("res_color", "")
    if "start" in cols:
        data["start"] = row_data.get("start", "")
    if "end" in cols:
        data["end"] = row_data.get("end", "")
    if "source_record_id" in cols:
        data["source_record_id"] = ""
    if "fetched_at" in cols:
        data["fetched_at"] = ""

    # 内容字段
    if "title" in cols:
        data["title"] = row_data.get("title", content_val)
    if "jiexi" in cols:
        data["jiexi"] = row_data.get("jiexi", "")
    if "xiao" in cols:
        data["xiao"] = row_data.get("xiao", content_val)
    if "code" in cols:
        data["code"] = row_data.get("code", "")
    if "hei" in cols:
        data["hei"] = row_data.get("hei", "")
    if "bai" in cols:
        data["bai"] = row_data.get("bai", "")
    if "zhong" in cols:
        data["zhong"] = row_data.get("zhong", "")
    if "ds" in cols:
        data["ds"] = row_data.get("ds", "")
    if "bo" in cols:
        data["bo"] = row_data.get("bo", "")
    if "image_url" in cols:
        data["image_url"] = ""

    # 标准 content 列（不用 title/xiao/hei 时写入）
    if "content" in cols:
        has_alt = ("title" in data or "xiao" in data or "hei" in data)
        if not has_alt:
            data["content"] = content_val
        elif "content" not in data:
            data["content"] = ""

    if not data:
        return False

    # 这里仍按 public 源表列做一次过滤，避免把脚本内部辅助字段写入目标表。
    data = {k: v for k, v in data.items() if k in cols}

    try:
        upsert_created_prediction_row(conn, table_name, data)
        return True
    except Exception as e:
        print(f"    INSERT ERROR[{table_name}]: {e}")
        conn.rollback()
        return False


# ── 单模块生成 ───────────────────────────────────────────
def generate_for_module(conn, config_key, cfg, lottery_type, draws,
                        zodiac_map, stats):
    """对指定模块 × 彩种 的所有 draws 生成预测"""
    from common import predict

    mode_id = cfg.default_modes_id
    table = cfg.default_table
    type_name = {1: "HK", 2: "Macau"}.get(lottery_type, f"type={lottery_type}")

    # 检查表是否存在
    cur = conn.execute(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name=%s)", (table,))
    if not cur.fetchone()["exists"]:
        stats["table_missing"].append(f"{config_key} → {table}")
        return

    success = 0
    fail = 0
    for i, draw in enumerate(draws):
        try:
            result = predict(
                config=cfg,
                res_code=draw["numbers_str"],
                db_path=DB_DSN,
                target_hit_rate=0.80,
            )
            row_data = parse_prediction_result(result, draw, zodiac_map, mode_id)
            if row_data:
                if upsert_row(conn, table, row_data, lottery_type):
                    success += 1
                else:
                    fail += 1
            else:
                fail += 1
        except Exception as e:
            fail += 1
            if fail == 1:
                stats["errors"].append(
                    f"{config_key}({mode_id}) type={lottery_type}: {e}")

        if (i + 1) % 50 == 0 or i == len(draws) - 1:
            print(f"\r    [{type_name}] {i+1}/{len(draws)} OK={success} FAIL={fail}", end="")

    if fail > 0:
        print(f"  ⚠ {fail} failures")
    else:
        print(f"  ✓ {success} rows")

    if success == 0 and fail > 0:
        stats["all_failed"].append(f"{config_key}({mode_id}) type={lottery_type}")


# ── 主流程 ────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="批量生成所有预测模块数据")
    parser.add_argument("--dry-run", action="store_true", help="只列出模块，不实际生成")
    parser.add_argument("--mechanism", help="只生成指定模块 (config_key)")
    args = parser.parse_args()

    print("=" * 60)
    print("批量预测数据生成 v4 — 全模块覆盖")
    print("=" * 60)

    conn = get_db_conn()
    print("[1] 连接数据库: OK")

    # 加载生肖映射（用于构建 res_sx）
    zodiac_map = load_fixed_data_map(conn, "生肖")
    print(f"[2] 生肖映射: {len(zodiac_map)} 生肖")

    # 读取 draws
    draws_hk = get_all_draws(conn, 1)
    draws_macau = get_all_draws(conn, 2)
    print(f"[3] 开奖数据: HK={len(draws_hk)} Macau={len(draws_macau)}")

    # 筛选模块
    if args.mechanism:
        if args.mechanism not in PREDICTION_CONFIGS:
            print(f"错误: 未知模块 '{args.mechanism}'")
            print(f"可用: {', '.join(sorted(PREDICTION_CONFIGS.keys()))}")
            return
        configs = [(args.mechanism, PREDICTION_CONFIGS[args.mechanism])]
    else:
        configs = sorted(PREDICTION_CONFIGS.items(),
                         key=lambda x: x[1].default_modes_id)

    print(f"[4] 模块数: {len(configs)}")
    if args.dry_run:
        print("\nDRY RUN — 只列出模块，不生成数据:\n")
        for key, cfg in configs:
            print(f"  {key:<25} modes_id={cfg.default_modes_id:<4} "
                  f"table={cfg.default_table}")
        return

    stats = {"table_missing": [], "errors": [], "all_failed": []}
    start_time = time.time()

    for idx, (config_key, cfg) in enumerate(configs):
        mode_id = cfg.default_modes_id
        table = cfg.default_table
        elapsed = time.time() - start_time
        eta = (elapsed / max(idx, 1)) * (len(configs) - idx) if idx > 0 else 0

        print(f"\n[{idx+1}/{len(configs)}] {config_key} "
              f"(modes_id={mode_id}, table={table}) "
              f"[{elapsed:.0f}s ETA {eta:.0f}s]")

        if draws_hk:
            generate_for_module(conn, config_key, cfg, 1, draws_hk,
                                zodiac_map, stats)
        else:
            print("  HK: 无开奖数据，跳过")

        if draws_macau:
            generate_for_module(conn, config_key, cfg, 2, draws_macau,
                                zodiac_map, stats)
        else:
            print("  Macau: 无开奖数据，跳过")

    # ── 报告 ─────────────────────────────────────────────
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"完成! 耗时 {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print("=" * 60)

    if stats["table_missing"]:
        print(f"\n⚠ 表缺失 ({len(stats['table_missing'])} 个):")
        for t in stats["table_missing"]:
            print(f"  - {t}")

    if stats["errors"]:
        print(f"\n⚠ 首次错误 ({len(stats['errors'])} 个):")
        for e in stats["errors"][:30]:
            print(f"  - {e}")
        if len(stats["errors"]) > 30:
            print(f"  ... 还有 {len(stats['errors'])-30} 个")

    if stats["all_failed"]:
        print(f"\n❌ 完全失败的模块 ({len(stats['all_failed'])} 个):")
        for f in stats["all_failed"]:
            print(f"  - {f}")

    if not stats.get("all_failed") and not stats.get("table_missing"):
        print("\n✓ 所有模块生成完成!")

    conn.close()


if __name__ == "__main__":
    main()
