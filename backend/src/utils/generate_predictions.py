"""
批量预测数据生成脚本 v3
=========================================================
核心问题：mode_payload 表中 HK(type=1) 和 Macau(type=2) 的
大量行缺少 res_code/res_sx 数据，导致后端过滤后前端显示为空。

解决方案：对每个缺少数据的模块 × 彩种：
  1. 调用 predict() 生成 1 行准确率 ~80% 的预测数据
  2. 再用直接生成法补足到至少 10 行
  3. 确保 res_code/res_sx 已填充

用法：python -X utf8 backend/src/utils/generate_predictions.py
"""

import json
import sys
import random
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = BACKEND_ROOT / "src"
PREDICT_ROOT = SRC_ROOT / "predict"
for p in (PREDICT_ROOT, SRC_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import psycopg
from psycopg.rows import dict_row
from utils.created_prediction_store import (
    count_created_prediction_rows,
    created_prediction_issue_exists,
    list_created_prediction_terms,
    upsert_created_prediction_row,
)

DB_DSN = "postgresql://postgres:2225427@localhost:5432/liuhecai"

# ── 工具 ───────────────────────────────────────────────
def get_conn():
    return psycopg.connect(DB_DSN, row_factory=dict_row)

def load_fixed_map(conn, sign_name):
    cur = conn.execute(
        "SELECT name, code FROM fixed_data WHERE sign = %s ORDER BY id", (sign_name,))
    result = {}
    for r in cur.fetchall():
        codes = [c.strip() for c in (r["code"] or "").split(",") if c.strip()]
        result[r["name"]] = codes
    return result

def number_to_zodiac(zodiac_map, num):
    num_str = str(num).zfill(2)
    for z, codes in zodiac_map.items():
        if num_str in codes:
            return z
    return ""

def number_to_color(color_map, num):
    num_str = str(num).zfill(2)
    for c, codes in color_map.items():
        if num_str in codes:
            return c
    return ""


def compute_three_period_window(term):
    raw_term = int(term)
    rem = raw_term % 3
    if rem == 2:
        start = raw_term
    elif rem == 0:
        start = raw_term - 1
    else:
        start = raw_term - 2
    return start, start + 2


def compute_prediction_window(mode_id, draw):
    if mode_id == 197:
        start, end = compute_three_period_window(draw["term"])
        return str(start), str(end)
    return "", ""


def build_prediction_seed(mode_id, game_type, draw, future=False):
    prefix = "future_" if future else ""
    start, end = compute_prediction_window(mode_id, draw)
    if start and end:
        return f"{prefix}{mode_id}_{game_type}_{draw['year']}_{start}_{end}"
    return f"{prefix}{mode_id}_{game_type}_{draw['year']}_{draw['term']}"


def attach_window_metadata(row_data, mode_id, draw):
    if not row_data:
        return row_data
    start, end = compute_prediction_window(mode_id, draw)
    if start and end:
        row_data["start"] = start
        row_data["end"] = end
    return row_data


def build_window_cache_key(row_data):
    start = str(row_data.get("start") or "").strip()
    end = str(row_data.get("end") or "").strip()
    if not start or not end:
        return None
    web_value = row_data.get("web", row_data.get("web_id", ""))
    return (
        str(row_data.get("type") or ""),
        str(row_data.get("year") or ""),
        str(web_value or ""),
        start,
        end,
    )


def load_existing_window_content_cache(conn, table_name, game_type):
    cols = get_table_columns(conn, table_name)
    if "content" not in cols or "start" not in cols or "end" not in cols:
        return {}

    cur = conn.execute(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='created' AND table_name=%s)",
        (table_name,),
    )
    if not cur.fetchone()["exists"]:
        return {}

    selected_columns = ["year", "type", "start", "end", "content"]
    if "web" in cols:
        selected_columns.append("web")
    if "web_id" in cols:
        selected_columns.append("web_id")

    selected_sql = ", ".join(f'"{column}"' for column in selected_columns)
    query = (
        f"SELECT {selected_sql} "
        f'FROM created."{table_name}" '
        "WHERE CAST(type AS TEXT) = %s "
        "AND COALESCE(CAST(start AS TEXT), '') != '' "
        "AND COALESCE(CAST(end AS TEXT), '') != '' "
        "AND COALESCE(CAST(content AS TEXT), '') != ''"
    )
    params = [str(game_type)]
    if "web" in cols:
        query += " AND CAST(web AS TEXT) = %s"
        params.append("4")
    elif "web_id" in cols:
        query += " AND CAST(web_id AS TEXT) = %s"
        params.append("4")

    rows = conn.execute(query, params).fetchall()
    cache = {}
    for row in rows:
        key = build_window_cache_key(row)
        if key and key not in cache:
            cache[key] = str(row["content"] or "")
    return cache


def normalize_window_content(row_data, window_content_cache):
    if not row_data or "content" not in row_data:
        return row_data

    key = build_window_cache_key(row_data)
    content = str(row_data.get("content") or "")
    if not key or not content:
        return row_data

    cached_content = window_content_cache.get(key)
    if cached_content:
        row_data["content"] = cached_content
    else:
        window_content_cache[key] = content
    return row_data

# ── 读取有效开奖 ──────────────────────────────────────
def get_valid_draws(conn, lottery_type_id, limit=20):
    """获取已开奖（is_opened=1）的有效历史开奖记录"""
    cur = conn.execute(
        """SELECT year, term, numbers FROM lottery_draws
           WHERE lottery_type_id = %s AND is_opened = 1 AND numbers ~ '^[0-9,]+$'
           ORDER BY year DESC, term DESC LIMIT %s""",
        (lottery_type_id, limit))
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

def get_next_unopened_draw(conn, lottery_type_id):
    """获取最近一期未开奖（is_opened=0）的开奖记录，用于生成下一期预测"""
    cur = conn.execute(
        """SELECT year, term, numbers FROM lottery_draws
           WHERE lottery_type_id = %s AND is_opened = 0
           ORDER BY year DESC, term DESC LIMIT 1""",
        (lottery_type_id,))
    r = cur.fetchone()
    if not r:
        return None
    nums = [n.strip() for n in r["numbers"].split(",") if n.strip()]
    try:
        ints = [int(n) for n in nums]
        if any(n < 1 or n > 49 for n in ints):
            return None
        processed = [str(n).zfill(2) for n in ints]
        return {
            "year": int(r["year"]),
            "term": int(r["term"]),
            "numbers": processed,
            "numbers_str": ",".join(processed),
        }
    except ValueError:
        return None

# ── 模块映射 ───────────────────────────────────────────
def build_module_map():
    from mechanisms import PREDICTION_CONFIGS
    legacy_modes = {
        43: "pt2xiao", 197: "3zxt", 38: "hllx",
        246: "7x7m", 45: "hbnx", 50: "yjzy",
        46: "lxzt", 8: "3ssx", 57: "dxzt",
        63: "jyzt", 54: "ptyw", 151: "9x1m",
        12: "3tou", 53: "xingte", 51: "4x8m",
        28: "danshuang", 31: "dssx", 65: "teduan",
        68: "yqmtm", 42: "shaxiao", 34: "tema",
        26: "qqsh", 58: "shabanbo", 20: "shawei",
        52: "szxj", 59: "djym", 61: "sjsx",
        3: "rccx", 244: "yyptj", 48: "wxzt",
        2: "6wei", 49: "jxzt", 56: "ptyx",
        108: "dxztt1", 331: "pmxjcz", 62: "juzi",
    }
    mode_to_config = {}
    for key, cfg in PREDICTION_CONFIGS.items():
        mid = cfg.default_modes_id
        if mid in legacy_modes and mid not in mode_to_config:
            mode_to_config[mid] = key
    result = {}
    for mid, lk in legacy_modes.items():
        result[lk] = {
            "modes_id": mid,
            "config_key": None if mid == 197 else mode_to_config.get(mid),
        }
    return result

# ── predict() 调用 ────────────────────────────────────
def call_predict(config_key, res_code, hit_rate=0.80):
    from common import predict
    from mechanisms import get_prediction_config
    cfg = get_prediction_config(config_key)
    if not cfg:
        return None
    r = predict(config=cfg, res_code=res_code, target_hit_rate=hit_rate, db_path=DB_DSN)
    return r

# ── 直接生成预测（降级/批量用） ──────────────────────────
def direct_predict(module_key, mode_id, draw, game_type, zodiac_map, color_map,
                   rng_override=None):
    """
    为某期开奖生成 ~80% 正确的预测内容。
    rng_override: 可选随机种子，用于批量生成时控制概率
    """
    nums = draw["numbers"]
    if not nums:
        return None
    special_num = nums[-1]
    special_zodiac = number_to_zodiac(zodiac_map, special_num)
    special_color = number_to_color(color_map, special_num)

    # 三期中特 (mode_id=197): 每 3 期为一组，组内 content 必须一致。
    # 将随机种子固定到组的第一期 (term % 3 == 2)，确保同组三期生成相同预测。
    seed = build_prediction_seed(mode_id, game_type, draw)
    rng = rng_override or random.Random(seed)
    is_hit = rng.random() < 0.80

    all_zodiacs = [number_to_zodiac(zodiac_map, n) for n in nums
                   if number_to_zodiac(zodiac_map, n)]
    all_unique_zodiacs = list(set(z for z in all_zodiacs if z))
    res_sx = ",".join(all_unique_zodiacs)
    res_color = ",".join(set(number_to_color(color_map, n) for n in nums
                             if number_to_color(color_map, n)))

    # ── 三期中特 (3zxt): JSON 数组 ["肖|号码列表"] ──
    if mode_id == 197:
        pool = all_unique_zodiacs if len(all_unique_zodiacs) >= 4 else list(zodiac_map.keys())
        chosen = rng.sample(pool, min(4, len(pool)))
        if special_zodiac and special_zodiac not in chosen:
            chosen[0] = special_zodiac
            rng.shuffle(chosen)
        items = []
        for z in chosen:
            codes = zodiac_map.get(z, [])
            items.append(f"{z}|{','.join(codes)}")
        return {
            "content": json.dumps(items, ensure_ascii=False),
            "res_code": draw["numbers_str"], "res_sx": res_sx, "res_color": res_color,
            "year": str(draw["year"]), "term": str(draw["term"]),
            "web": "4", "type": str(game_type), "table_modes_id": str(mode_id),
        }

    # ── 黑白无双 (hbnx): 拆分为 hei/bai ──
    if mode_id == 45:
        all_z = all_unique_zodiacs if all_unique_zodiacs else list(zodiac_map.keys())
        rng.shuffle(all_z)
        if len(all_z) >= 6:
            hei_pick = sorted(rng.sample(all_z, 3))
            bai_pick = sorted(rng.sample([z for z in all_z if z not in hei_pick], 3))
        else:
            hei_pick = sorted(rng.sample(list(zodiac_map.keys()), 3))
            bai_pick = sorted(rng.sample([z for z in zodiac_map if z not in hei_pick], 3))
        return {
            "content": "", "hei": ",".join(hei_pick), "bai": ",".join(bai_pick),
            "res_code": draw["numbers_str"], "res_sx": res_sx, "res_color": res_color,
            "year": str(draw["year"]), "term": str(draw["term"]),
            "web": "4", "type": str(game_type), "table_modes_id": str(mode_id),
        }

    # ── 七肖七码 (246): JSON 对象 {"xiao":"...","code":"..."} ──
    if mode_id == 246:
        available = list(zodiac_map.keys())
        rng.shuffle(available)
        xiao_pick = available[:7]
        codes_all = []
        for z in xiao_pick:
            z_codes = zodiac_map.get(z, [])
            if z_codes:
                codes_all.append(rng.choice(z_codes))
        if not is_hit and special_zodiac and special_zodiac not in xiao_pick:
            xiao_pick[0] = special_zodiac
            rng.shuffle(xiao_pick)
        return {
            "xiao": json.dumps({"xiao": ",".join(xiao_pick), "ping": "",
                                 "code": ",".join(codes_all)}, ensure_ascii=False),
            "res_code": draw["numbers_str"], "res_sx": res_sx, "res_color": res_color,
            "year": str(draw["year"]), "term": str(draw["term"]),
            "web": "4", "type": str(game_type), "table_modes_id": str(mode_id),
        }

    # ── 六肖中特 (46): 6 个逗号分隔生肖 ──
    if mode_id == 46:
        available = list(zodiac_map.keys())
        rng.shuffle(available)
        six = available[:6]
        if not is_hit and special_zodiac and special_zodiac not in six:
            six[0] = special_zodiac
            rng.shuffle(six)
        return {
            "content": ",".join(six),
            "res_code": draw["numbers_str"], "res_sx": res_sx, "res_color": res_color,
            "year": str(draw["year"]), "term": str(draw["term"]),
            "web": "4", "type": str(game_type), "table_modes_id": str(mode_id),
        }

    # ── 三色生肖 (8): JSON 数组 ["色肖|zodiacs",...] ──
    if mode_id == 8:
        all_colors = ["红肖", "蓝肖", "绿肖"]
        rng.shuffle(all_colors)
        items = []
        for c in all_colors[:2]:
            subset = list(zodiac_map.keys())
            rng.shuffle(subset)
            items.append(f"{c}|{','.join(subset[:4])}")
        return {
            "content": json.dumps(items, ensure_ascii=False),
            "res_code": draw["numbers_str"], "res_sx": res_sx, "res_color": res_color,
            "year": str(draw["year"]), "term": str(draw["term"]),
            "web": "4", "type": str(game_type), "table_modes_id": str(mode_id),
        }

    # ── 默认：简单生肖内容 ──
    content = special_zodiac
    if not is_hit:
        wrong = [z for z in zodiac_map.keys() if z != special_zodiac]
        content = rng.choice(wrong) if wrong else special_zodiac

    return {
        "content": content,
        "res_code": draw["numbers_str"], "res_sx": res_sx, "res_color": res_color,
        "year": str(draw["year"]), "term": str(draw["term"]),
        "web": "4", "type": str(game_type), "table_modes_id": str(mode_id),
    }


def direct_predict_future(module_key, mode_id, draw, game_type, zodiac_map, color_map,
                          rng_override=None):
    """
    为未开奖期生成不依赖真实开奖结果的降级预测。

    注意：
    1. 这里禁止读取 next_draw.numbers 来反推预测内容。
    2. 仅按期号做确定性随机，保证同一期重复生成时结果稳定。
    3. res_code / res_sx / res_color 一律留空，由调用方最终再兜底清空。
    """
    del module_key, color_map

    # 三期中特 (mode_id=197): 每 3 期为一组，将种子固定到组的第一期
    seed = build_prediction_seed(mode_id, game_type, draw, future=True)
    rng = rng_override or random.Random(seed)
    all_zodiacs = list(zodiac_map.keys())
    rng.shuffle(all_zodiacs)

    base = {
        "year": str(draw["year"]),
        "term": str(draw["term"]),
        "web": "4",
        "type": str(game_type),
        "table_modes_id": str(mode_id),
        "res_code": "",
        "res_sx": "",
        "res_color": "",
    }

    if mode_id == 197:
        chosen = all_zodiacs[:4]
        items = [f"{z}|{','.join(zodiac_map.get(z, []))}" for z in chosen]
        return {**base, "content": json.dumps(items, ensure_ascii=False)}

    if mode_id == 45:
        hei_pick = sorted(all_zodiacs[:3])
        bai_pick = sorted(all_zodiacs[3:6])
        return {**base, "content": "", "hei": ",".join(hei_pick), "bai": ",".join(bai_pick)}

    if mode_id == 246:
        xiao_pick = all_zodiacs[:7]
        codes_all = []
        for z in xiao_pick:
            z_codes = zodiac_map.get(z, [])
            if z_codes:
                codes_all.append(rng.choice(z_codes))
        return {
            **base,
            "xiao": json.dumps(
                {"xiao": ",".join(xiao_pick), "ping": "", "code": ",".join(codes_all)},
                ensure_ascii=False,
            ),
        }

    if mode_id == 46:
        return {**base, "content": ",".join(all_zodiacs[:6])}

    if mode_id == 8:
        items = [
            f"红肖|{','.join(all_zodiacs[:4])}",
            f"蓝肖|{','.join(all_zodiacs[4:8])}",
        ]
        return {**base, "content": json.dumps(items, ensure_ascii=False)}

    return {**base, "content": all_zodiacs[0] if all_zodiacs else ""}

# ── 解析 predict() 结果 ───────────────────────────────
def parse_predict_result(result, draw, game_type, zodiac_map, mode_id):
    if not result:
        return None
    raw_content = result["prediction"]["content"]

    nums = draw["numbers"]
    all_zodiacs = [number_to_zodiac(zodiac_map, n) for n in nums
                   if number_to_zodiac(zodiac_map, n)]
    res_sx = ",".join(set(z for z in all_zodiacs if z))

    base = {
        "res_code": draw["numbers_str"],
        "res_sx": res_sx,
        "year": str(draw["year"]),
        "term": str(draw["term"]),
        "web": "4",
        "type": str(game_type),
        "table_modes_id": str(mode_id),
    }

    # 处理结构化内容：
    # 1. 旧表里有不少玩法本来就是多列（title/jiexi、xiao_1/xiao_2、hei/bai）
    # 2. 这里必须把结构化字段原样带下去，不能再整体 json.dumps 成一个 content
    #    否则后续插入时就会把整段 JSON 塞进单列，前端只能看到“{"xiao_1": ...}”这种错乱文本。
    if isinstance(raw_content, dict):
        structured = dict(base)
        for key, value in raw_content.items():
            if isinstance(value, list):
                structured[key] = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, dict):
                structured[key] = json.dumps(value, ensure_ascii=False)
            elif value is None:
                structured[key] = ""
            else:
                structured[key] = str(value)

        structured.setdefault("content", "")
        return structured
    elif isinstance(raw_content, list):
        return {**base, "content": json.dumps(raw_content, ensure_ascii=False)}
    else:
        return {**base, "content": str(raw_content)}

# ── 插入到 mode_payload 表（动态适配不同表结构） ──────
# 不同 mode_payload 表有不同的列名体系：
#   content    → 标准表 (43, 8, 57, 151, 12, 53, 51, 28, 2, 38, 46)
#   content    → 带 start/end (197), 带 title/jiexi (50)
#   xiao/code  → 7x7m (246)
#   hei/bai    → 黑白无双 (45)
#   xiao_1/xiao_2 → 单双四肖 (31)
_TABLE_SCHEMA_CACHE = {}

def get_table_columns(conn, table_name):
    """缓存查询结果加速"""
    if table_name not in _TABLE_SCHEMA_CACHE:
        cur = conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=%s", (table_name,))
        _TABLE_SCHEMA_CACHE[table_name] = {r["column_name"] for r in cur.fetchall()}
    return _TABLE_SCHEMA_CACHE[table_name]


def detect_content_column(cols):
    """根据列名表确定预测内容的存放列"""
    for candidate in ["content", "xiao", "title", "hei", "xiao_1"]:
        if candidate in cols:
            return candidate
    return "content"  # fallback


def build_insert_data(content, row_data, cols):
    """构建列名→值的映射，只插入表中存在的列"""
    data = {}
    # 基础列
    for c in ["res_code", "res_sx", "year", "term", "type", "web"]:
        if c in cols:
            data[c] = row_data[c]
    # 内容列
    content_col = detect_content_column(cols)
    # 如果 row_data 直接提供了该列的值（如 xiao/code/hei/bai），优先使用
    if content_col != "content" and content_col in row_data and row_data[content_col]:
        data[content_col] = row_data[content_col]
    else:
        data[content_col] = content
    # 结构化玩法（例如 title/jiexi、xiao/code、xiao_1/xiao_2）需要把 row_data 中同名字段继续写回。
    # 这里统一做一次“列存在才透传”，避免后面每加一种玩法都写一套硬编码。
    for key, value in row_data.items():
        if key in cols and key not in data and value not in (None, ""):
            data[key] = value
    # 可选列
    for c, v in [("web_id", 4), ("modes_id", int(row_data["table_modes_id"])),
                  ("status", 1), ("res_color", row_data.get("res_color", "")),
                  ("start", row_data.get("start", "")), ("end", row_data.get("end", ""))]:
        if c in cols:
            data[c] = v
    # 特殊处理：hei/bai — 优先使用 row_data 中的专用值
    if "hei" in cols and "bai" in cols:
        data["hei"] = row_data.get("hei", content)
        data["bai"] = row_data.get("bai", content)
    # 特殊处理：xiao_1/xiao_2
    if "xiao_1" in cols and "xiao_2" in cols:
        data["xiao_1"] = row_data.get("xiao_1", content)
        data["xiao_2"] = row_data.get("xiao_2", content)
    return data


def insert_row(conn, table_name, row_data):
    cols = get_table_columns(conn, table_name)
    content = row_data.get("content", "")
    data = build_insert_data(content, row_data, cols)

    if not data:
        return

    upsert_created_prediction_row(conn, table_name, data)

# ── 主生成逻辑 ────────────────────────────────────────
def fill_module_for_type(conn, module_key, module_info, game_type,
                         draws, zodiac_map, color_map):
    """
    为指定模块 × 彩种填充数据。
    返回生成行数。
    """
    mode_id = module_info["modes_id"]
    config_key = module_info["config_key"]
    table = f"mode_payload_{mode_id}"

    # 表是否存在
    cur = conn.execute(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name=%s)", (table,))
    if not cur.fetchone()["exists"]:
        return 0

    existing_filled = count_created_prediction_rows(
        conn,
        table,
        lottery_type=str(game_type),
        web_value="4",
        only_filled=True,
    )
    filled_terms = list_created_prediction_terms(
        conn,
        table,
        lottery_type=str(game_type),
        web_value="4",
        only_filled=True,
    )

    target_rows = max(10, existing_filled)
    needed = target_rows - existing_filled

    if needed <= 0 and len(filled_terms) >= 5:
        return 0

    print(f"    type={game_type}: 已有 {existing_filled} 行有效，目标 {target_rows} 行")

    generated = 0
    window_content_cache = load_existing_window_content_cache(conn, table, game_type)

    for draw in draws:
        if generated >= needed:
            break
        dk = (draw["year"], draw["term"])
        if dk in filled_terms:
            continue

        row_data = None

        # 只要玩法有正式机制，就优先对每一期都走 predict()。
        # 之前仅第一条使用 predict()，后续全部降级为 direct_predict()，
        # 会把 24码、单双四肖、文本类玩法错误压缩成“单生肖/单字符串”。
        if config_key:
            try:
                result = call_predict(config_key, draw["numbers_str"])
                row_data = parse_predict_result(result, draw, game_type, zodiac_map, mode_id)
                row_data = attach_window_metadata(row_data, mode_id, draw)
                if row_data:
                    print(f"      predict[{draw['year']}-{draw['term']}] 成功", end="")
            except Exception as e:
                print(f"      predict 失败 ({e})，降级", end="")

        # 降级/后续调用用直接生成
        if row_data is None:
            row_data = direct_predict(module_key, mode_id, draw, game_type,
                                      zodiac_map, color_map)
            row_data = attach_window_metadata(row_data, mode_id, draw)
            if row_data:
                print(f"      direct[{draw['year']}-{draw['term']}]", end="")

        if row_data:
            row_data = normalize_window_content(row_data, window_content_cache)
            insert_row(conn, table, row_data)
            generated += 1
            print()

    if generated > 0:
        print(f"    → +{generated} 行")

    return generated

def generate_next_prediction(conn, module_key, module_info, game_type,
                              zodiac_map, color_map):
    """
    为下一期未开奖的 draw 生成 1 条预测数据。
    res_code / res_sx 留空，不泄露未来开奖结果。
    """
    next_draw = get_next_unopened_draw(conn, game_type)
    if not next_draw:
        return 0

    mode_id = module_info["modes_id"]
    config_key = module_info["config_key"]
    table = f"mode_payload_{mode_id}"

    # 表是否存在
    cur = conn.execute(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name=%s)", (table,))
    if not cur.fetchone()["exists"]:
        return 0

    # created schema 中如果已经生成过该期预测，则不重复写入。
    if created_prediction_issue_exists(
        conn,
        table,
        lottery_type=str(game_type),
        year=str(next_draw["year"]),
        term=str(next_draw["term"]),
        web_value="4",
    ):
        return 0

    row_data = None
    if config_key:
        try:
            # 未开奖期禁止把真实号码喂给 predict()，否则等同于提前泄露未来结果。
            result = call_predict(config_key, None)
            row_data = parse_predict_result(result, next_draw, game_type, zodiac_map, mode_id)
            row_data = attach_window_metadata(row_data, mode_id, next_draw)
        except:
            pass

    if row_data is None:
        row_data = direct_predict_future(module_key, mode_id, next_draw, game_type,
                                         zodiac_map, color_map)
        row_data = attach_window_metadata(row_data, mode_id, next_draw)

    if row_data:
        # ★ 关键：清空 res_code / res_sx，不泄露未来开奖结果
        row_data["res_code"] = ""
        row_data["res_sx"] = ""
        row_data["res_color"] = ""
        row_data = normalize_window_content(
            row_data,
            load_existing_window_content_cache(conn, table, game_type),
        )
        insert_row(conn, table, row_data)
        print(f"    → 下期预测 {next_draw['year']}-{next_draw['term']}")
        return 1

    return 0

# ── 验证正确率 ────────────────────────────────────────
def verify_accuracy(conn):
    print("\n" + "=" * 60)
    print("正确率验证")
    print("=" * 60)

    zodiac_map = load_fixed_map(conn, "生肖")
    checks = [
        (43, "两肖平特王"), (197, "三期中特"), (38, "双波中特"),
        (46, "六肖中特"), (56, "平特一肖"), (151, "九肖一码"),
        (54, "平特尾"), (20, "绝杀一尾"),
    ]

    for mid, name in checks:
        table = f"mode_payload_{mid}"
        print(f"\n{name} ({table})")
        for tid in [1, 2, 3]:
            cur = conn.execute(
                f'SELECT content, res_sx FROM "{table}" WHERE type=%s '
                f"AND res_code IS NOT NULL AND res_code != %s "
                f"ORDER BY CAST(year AS INTEGER) DESC, CAST(term AS INTEGER) DESC LIMIT 20",
                (str(tid), ""))
            rows = cur.fetchall()
            if not rows:
                print(f"  type={tid}: 无数据")
                continue
            correct = 0
            for r in rows:
                content = r["content"] or ""
                res_sx = r["res_sx"] or ""
                try:
                    parsed = json.loads(content)
                    txt = json.dumps(parsed, ensure_ascii=False) if isinstance(parsed, (dict, list)) else str(parsed)
                except (json.JSONDecodeError, TypeError):
                    txt = str(content)
                sx_list = [s.strip() for s in res_sx.split(",") if s.strip()]
                if any(sx in txt for sx in sx_list):
                    correct += 1
            acc = correct / len(rows) * 100
            print(f"  type={tid}: {correct}/{len(rows)} ({acc:.1f}%)")

# ── 主流程 ────────────────────────────────────────────
def main():
    print("=" * 60)
    print("批量预测数据生成 v3")
    print("=" * 60)

    conn = get_conn()
    print("[1/4] 连接数据库: OK")

    module_map = build_module_map()
    zodiac_map = load_fixed_map(conn, "生肖")
    color_map = load_fixed_map(conn, "波色")
    print(f"[2/4] 映射: {len(module_map)} 模块, {len(zodiac_map)} 生肖")

    type_names = {1: "香港彩", 2: "澳门彩", 3: "台湾彩"}
    draws_by_type = {}
    for tid in [1, 2, 3]:
        draws = get_valid_draws(conn, tid, limit=20)
        draws_by_type[tid] = draws
        if draws:
            d = draws[0]
            print(f"[3/4] {type_names[tid]}: 最新 {d['year']}-{d['term']} ({d['numbers_str']})")
        else:
            print(f"[3/4] {type_names[tid]}: 无有效开奖")

    print("[4/4] 生成预测数据...")
    total = 0

    for module_key, module_info in sorted(module_map.items()):
        mode_id = module_info["modes_id"]
        ck = module_info["config_key"] or "无"
        print(f"\n{module_key} (modes_id={mode_id}, config={ck})")

        for tid in [1, 2, 3]:
            draws = draws_by_type.get(tid, [])
            if not draws:
                print(f"  {type_names[tid]}: 无开奖数据")
                continue
            n = fill_module_for_type(conn, module_key, module_info, tid,
                                     draws, zodiac_map, color_map)
            if n is not None:
                total += n
            # ★ 生成下一期预测（仅 type=3 台湾彩，res_code/res_sx 留空）
            if tid == 3:
                n2 = generate_next_prediction(conn, module_key, module_info, tid,
                                               zodiac_map, color_map)
                if n2:
                    total += n2
            n = fill_module_for_type(conn, module_key, module_info, tid,
                                     draws, zodiac_map, color_map)
            if n is not None:
                total += n

    verify_accuracy(conn)
    conn.close()
    print(f"\n总共生成: {total} 行")
    print("完成!")

if __name__ == "__main__":
    main()
