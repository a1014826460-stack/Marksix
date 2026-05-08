"""为香港彩(type=1) / 澳门彩(type=2)快速生成前端页面所需的预测模块数据。

设计说明：
1. 该脚本只服务前端展示，不追求复杂预测准确率。
2. 直接基于 `public.lottery_draws` 的真实历史开奖号生成 10 条数据。
3. 不解析旧的历史预测内容，不走 `predict()`，也不调用后端 HTTP API。
4. 不修改 `public.mode_payload_*`，统一写入 `created.mode_payload_*`。
5. 明确避开 `backend/src/app.py`，方便后端重构时互不干扰。

适用范围：
- 仅生成当前前端页面真正会读取的 35 个预测模块。
- 仅处理 `type=1`（香港彩）和 `type=2`（澳门彩）。
- 每个模块、每个彩种只保留最近 10 条。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = BACKEND_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from db import connect, resolve_database_target  # noqa: E402
from utils.generate_predictions import (  # noqa: E402
    get_valid_draws,
    insert_row,
    load_fixed_map,
    number_to_color,
    number_to_zodiac,
)
from utils.created_prediction_store import (  # noqa: E402
    CREATED_SCHEMA_NAME,
    quote_identifier,
    quote_qualified_identifier,
    table_column_names,
)


DEFAULT_DB_TARGET = resolve_database_target(None)
SUPPORTED_TYPES = (1, 2)
ROWS_PER_MODULE = 10

# 当前前端页面真正会读取的旧模块清单。
# 这里直接对齐 frontend/lib/legacy-modules.ts，避免站点配置表与前端读取范围不一致。
FRONTEND_MODULES = (
    {"mode_id": 43, "mechanism_key": "legacy_pt2xiao"},
    {"mode_id": 197, "mechanism_key": "legacy_3zxt"},
    {"mode_id": 38, "mechanism_key": "legacy_hllx"},
    {"mode_id": 44, "mechanism_key": "legacy_7x7m"},
    {"mode_id": 45, "mechanism_key": "legacy_hbnx"},
    {"mode_id": 50, "mechanism_key": "legacy_yjzy"},
    {"mode_id": 46, "mechanism_key": "legacy_lxzt"},
    {"mode_id": 8, "mechanism_key": "legacy_3ssx"},
    {"mode_id": 57, "mechanism_key": "legacy_dxzt"},
    {"mode_id": 63, "mechanism_key": "legacy_jyzt"},
    {"mode_id": 54, "mechanism_key": "legacy_ptyw"},
    {"mode_id": 151, "mechanism_key": "legacy_9x1m"},
    {"mode_id": 12, "mechanism_key": "legacy_3tou"},
    {"mode_id": 53, "mechanism_key": "legacy_xingte"},
    {"mode_id": 51, "mechanism_key": "legacy_4x8m"},
    {"mode_id": 28, "mechanism_key": "legacy_danshuang"},
    {"mode_id": 31, "mechanism_key": "legacy_dssx"},
    {"mode_id": 65, "mechanism_key": "legacy_teduan"},
    {"mode_id": 68, "mechanism_key": "legacy_yqmtm"},
    {"mode_id": 42, "mechanism_key": "legacy_shaxiao"},
    {"mode_id": 34, "mechanism_key": "legacy_tema"},
    {"mode_id": 26, "mechanism_key": "legacy_qqsh"},
    {"mode_id": 58, "mechanism_key": "legacy_shabanbo"},
    {"mode_id": 20, "mechanism_key": "legacy_shawei"},
    {"mode_id": 52, "mechanism_key": "legacy_szxj"},
    {"mode_id": 59, "mechanism_key": "legacy_djym"},
    {"mode_id": 61, "mechanism_key": "legacy_sjsx"},
    {"mode_id": 3, "mechanism_key": "legacy_rccx"},
    {"mode_id": 244, "mechanism_key": "legacy_yyptj"},
    {"mode_id": 48, "mechanism_key": "legacy_wxzt"},
    {"mode_id": 2, "mechanism_key": "legacy_6wei"},
    {"mode_id": 49, "mechanism_key": "legacy_jxzt"},
    {"mode_id": 56, "mechanism_key": "legacy_ptyx"},
    {"mode_id": 108, "mechanism_key": "legacy_dxztt1"},
    {"mode_id": 331, "mechanism_key": "legacy_pmxjcz"},
    {"mode_id": 62, "mechanism_key": "legacy_juzi"},
    {"mode_id": 44, "mechanism_key": "legacy_qxbm"},
    {"mode_id": 44, "mechanism_key": "legacy_wxbm"},
)


def issue_text(draw: dict[str, Any]) -> str:
    return f"{int(draw['year'])}{int(draw['term']):03d}"


def special_code(draw: dict[str, Any]) -> str:
    return str(draw["numbers"][-1])


def all_codes_csv(draw: dict[str, Any]) -> str:
    return str(draw["numbers_str"])


def all_zodiacs(draw: dict[str, Any], zodiac_map: dict[str, list[str]]) -> list[str]:
    """按开奖号码顺序返回去重后的生肖列表。"""
    ordered: list[str] = []
    seen: set[str] = set()
    for code in draw["numbers"]:
        sx = number_to_zodiac(zodiac_map, code)
        if sx and sx not in seen:
            ordered.append(sx)
            seen.add(sx)
    return ordered


def special_zodiac(draw: dict[str, Any], zodiac_map: dict[str, list[str]]) -> str:
    return number_to_zodiac(zodiac_map, special_code(draw)) or ""


def special_color(draw: dict[str, Any], color_map: dict[str, list[str]]) -> str:
    return number_to_color(color_map, special_code(draw)) or ""


def zodiac_codes(zodiac_map: dict[str, list[str]], zodiac_name: str) -> list[str]:
    return list(zodiac_map.get(zodiac_name, []))


def wrap_base_row(mode_id: int, lottery_type: int, draw: dict[str, Any]) -> dict[str, Any]:
    """构造所有模块共用的基础字段。"""
    return {
        "type": str(lottery_type),
        "year": str(draw["year"]),
        "term": str(draw["term"]),
        "web": "4",
        "web_id": "4",
        "table_modes_id": str(mode_id),
        "modes_id": str(mode_id),
        "status": 1,
        "res_code": all_codes_csv(draw),
        "res_sx": "",
        "res_color": "",
    }


def build_array_payload(items: list[str]) -> str:
    return json.dumps(items, ensure_ascii=False)


def build_object_payload(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)


def pick_distinct_zodiacs(draw: dict[str, Any], zodiac_map: dict[str, list[str]], count: int) -> list[str]:
    """优先使用当期实际生肖，不足时补齐其他生肖。"""
    actual = all_zodiacs(draw, zodiac_map)
    pool = list(actual)
    for zodiac_name in zodiac_map.keys():
        if zodiac_name not in pool:
            pool.append(zodiac_name)
    return pool[:count]


def build_lightweight_row(
    mode_id: int,
    lottery_type: int,
    draw: dict[str, Any],
    zodiac_map: dict[str, list[str]],
    color_map: dict[str, list[str]],
) -> dict[str, Any]:
    """按前端实际展示格式构造一行轻量预测数据。

    这里的目标是“结构对、前端能显示”，不是复刻旧算法。
    因此绝大多数模块直接使用真实特码生肖/号码来拼装展示内容。
    """
    base = wrap_base_row(mode_id, lottery_type, draw)
    sx = special_zodiac(draw, zodiac_map)
    color = special_color(draw, color_map)
    code = special_code(draw)
    base["res_sx"] = ",".join(
        [number_to_zodiac(zodiac_map, item) or "" for item in draw["numbers"]]
    )
    base["res_color"] = ",".join(
        [number_to_color(color_map, item) or "" for item in draw["numbers"]]
    )
    # 三期中特：前端期待 JSON 数组 ["生肖|号码列表", ...]
    if mode_id == 197:
        chosen = pick_distinct_zodiacs(draw, zodiac_map, 4)
        base["content"] = build_array_payload(
            [f"{item}|{','.join(zodiac_codes(zodiac_map, item))}" for item in chosen]
        )
        return base

    # 七肖七码 / 五行八码：前端当前都从 mode_payload_44.content 解析数组。
    if mode_id == 44:
        chosen = pick_distinct_zodiacs(draw, zodiac_map, 7)
        payload: list[str] = []
        for item in chosen:
            codes = zodiac_codes(zodiac_map, item)
            payload.append(f"{item}|{codes[0] if codes else code}")
        base["content"] = build_array_payload(payload)
        return base

    # 黑白无双：hei / bai 两列
    if mode_id == 45:
        chosen = pick_distinct_zodiacs(draw, zodiac_map, 6)
        base["content"] = ""
        base["hei"] = ",".join(chosen[:3])
        base["bai"] = ",".join(chosen[3:6])
        return base

    # 一句真言：前端读 title / jiexi
    if mode_id == 50:
        base["title"] = f"{sx}行千里，{color}波有玄机"
        base["jiexi"] = f"主看{sx}{code}"
        base["content"] = ""
        return base

    # 单双四肖：前端需要 xiao_1 / xiao_2
    if mode_id == 31:
        chosen = pick_distinct_zodiacs(draw, zodiac_map, 8)
        base["xiao_1"] = "".join(chosen[:4])
        base["xiao_2"] = "".join(chosen[4:8])
        base["content"] = ""
        return base

    # 平特尾、三头中特：前端期待数组 JSON
    if mode_id == 54:
        tail = code[-1]
        base["content"] = build_array_payload([f"{tail}|{tail}"])
        return base

    if mode_id == 12:
        heads = sorted({item[0] for item in draw["numbers"]})[:3]
        base["content"] = build_array_payload([f"{head}|{head}" for head in heads])
        return base

    # 四季生肖：前端旧脚本会解析成 ["春|兔虎龙", ...]
    if mode_id == 61:
        base["content"] = build_array_payload([
            "春|兔虎龙",
            "夏|羊蛇马",
            "秋|狗鸡猴",
            "冬|猪牛鼠",
        ])
        return base

    # 幽默：前端会解析 JSON 对象
    if mode_id == 59:
        base["content"] = build_object_payload({
            "title": f"{sx}{code}看点十足",
            "content": f"主攻{sx}{code}",
        })
        return base

    # 一语破天机：旧前端直接读取 content 文本
    if mode_id == 244:
        base["content"] = f"{sx}{code}一语中的"
        return base

    # 大小中特附加版：旧前端需要 tou / content 两个 JSON 字段
    if mode_id == 108:
        number_value = int(code)
        size_label = "大" if number_value >= 25 else "小"
        head_label = code[0]
        if 10 <= number_value <= 19:
            head_text = "1头"
        elif 20 <= number_value <= 29:
            head_text = "2头"
        elif 30 <= number_value <= 39:
            head_text = "3头"
        elif 40 <= number_value <= 49:
            head_text = "4头"
        else:
            head_text = "0头"
        base["tou"] = build_array_payload([head_text])
        base["content"] = build_array_payload([f"{size_label}|{code}"])
        return base

    # 跑马图：旧前端需要 title / content / x7m14
    if mode_id == 331:
        chosen = pick_distinct_zodiacs(draw, zodiac_map, 7)
        x7m14_payload: list[str] = []
        ma_list: list[str] = []
        for item in chosen:
            codes = zodiac_codes(zodiac_map, item)[:2]
            if not codes:
                codes = [code]
            ma_list.extend(codes)
            x7m14_payload.append(f"{item}|{','.join(codes)}")
        base["title"] = sx or "测"
        base["content"] = f"主看{sx}{code}，兼顾{''.join(chosen[:3])}"
        base["x7m14"] = build_array_payload(x7m14_payload)
        base["image_url"] = ""
        return base

    # 四字玄机：文本模块
    if mode_id == 52:
        phrases = ["顺水推舟", "马到功成", "稳操胜券", "一击即中"]
        base["content"] = phrases[int(code) % len(phrases)]
        return base

    # 欲钱买特码 / 句子类文本
    if mode_id in {62, 68}:
        base["content"] = f"欲钱买{sx}的生肖"
        return base

    # 特码段数
    if mode_id == 65:
        num = int(code)
        if num <= 12:
            base["content"] = "1段"
        elif num <= 24:
            base["content"] = "2段"
        elif num <= 36:
            base["content"] = "3段"
        else:
            base["content"] = "4段"
        return base

    # 三色生肖
    if mode_id == 8:
        first = pick_distinct_zodiacs(draw, zodiac_map, 8)
        base["content"] = build_array_payload([
            f"红肖|{','.join(first[:4])}",
            f"蓝肖|{','.join(first[4:8])}",
        ])
        return base

    # 其余生肖类模块：直接给出若干生肖或号码，保证前端有内容。
    if mode_id == 151:
        chosen = pick_distinct_zodiacs(draw, zodiac_map, 9)
        parts = []
        for item in chosen:
            codes = zodiac_codes(zodiac_map, item)
            parts.append(f"{item}|{codes[0] if codes else code}")
        base["content"] = build_array_payload(parts)
        return base

    if mode_id == 34:
        # 经典 24 码至少给足 24 个号码，前端展示才不会显得残缺。
        numbers: list[str] = []
        for zodiac_name in pick_distinct_zodiacs(draw, zodiac_map, 6):
            numbers.extend(zodiac_codes(zodiac_map, zodiac_name)[:4])
        base["content"] = ",".join(numbers[:24])
        return base

    if mode_id == 38:
        base["content"] = color or "red"
        return base

    if mode_id == 28:
        base["content"] = "单" if int(code) % 2 else "双"
        return base

    if mode_id == 20:
        base["content"] = code[-1]
        return base

    if mode_id == 48:
        chosen = pick_distinct_zodiacs(draw, zodiac_map, 5)
        base["content"] = "".join(chosen)
        return base

    if mode_id == 49:
        chosen = pick_distinct_zodiacs(draw, zodiac_map, 9)
        base["content"] = "".join(chosen)
        return base

    if mode_id in {3, 42, 43, 46, 51, 53, 56, 57, 58, 63}:
        chosen = pick_distinct_zodiacs(draw, zodiac_map, 6)
        if mode_id == 43:
            base["content"] = ",".join(chosen[:2])
        elif mode_id == 51:
            base["content"] = "".join(chosen[:4])
        else:
            base["content"] = ",".join(chosen[:3])
        return base

    # 未单独定义的剩余模块，统一回退到特码生肖。
    base["content"] = sx or code
    return base


def load_frontend_modules() -> list[dict[str, Any]]:
    """直接返回前端真实使用的模块清单。

    这里不再依赖 site_prediction_modules，避免“站点配置表只有 35 个模块，
    但前端页面实际还会额外读取 legacy 模块”时出现漏生成。
    """
    return [dict(item) for item in FRONTEND_MODULES]


def created_row_count(conn: Any, table_name: str, lottery_type: int) -> int:
    columns = set(table_column_names(conn, CREATED_SCHEMA_NAME, table_name))
    table_ref = quote_qualified_identifier(CREATED_SCHEMA_NAME, table_name)
    where_parts = ['CAST("type" AS TEXT) = %s']
    params: list[Any] = [str(lottery_type)]
    if "web" in columns:
        where_parts.append('CAST("web" AS TEXT) = %s')
        params.append("4")
    elif "web_id" in columns:
        where_parts.append('CAST("web_id" AS TEXT) = %s')
        params.append("4")
    row = conn.execute(
        f"SELECT COUNT(*) AS total FROM {table_ref} WHERE {' AND '.join(where_parts)}",
        params,
    ).fetchone()
    return int(row["total"] or 0)


def trim_created_rows(conn: Any, table_name: str, lottery_type: int, keep_rows: int) -> int:
    """只保留最近 keep_rows 条，避免一个模块越积越多。"""
    columns = set(table_column_names(conn, CREATED_SCHEMA_NAME, table_name))
    table_ref = quote_qualified_identifier(CREATED_SCHEMA_NAME, table_name)
    where_parts = ['CAST("type" AS TEXT) = %s']
    params: list[Any] = [str(lottery_type)]
    if "web" in columns:
        where_parts.append('CAST("web" AS TEXT) = %s')
        params.append("4")
    elif "web_id" in columns:
        where_parts.append('CAST("web_id" AS TEXT) = %s')
        params.append("4")
    rows = conn.execute(
        f"""
        SELECT id
        FROM {table_ref}
        WHERE {' AND '.join(where_parts)}
        ORDER BY CAST(year AS INTEGER) DESC, CAST(term AS INTEGER) DESC, id DESC
        """,
        params,
    ).fetchall()
    if len(rows) <= keep_rows:
        return 0
    stale_ids = [row["id"] for row in rows[keep_rows:]]
    deleted = 0
    for stale_id in stale_ids:
        conn.execute(
            f"DELETE FROM {table_ref} WHERE id = %s",
            (stale_id,),
        )
        deleted += 1
    conn.commit()
    return deleted


def generate_for_type(
    conn: Any,
    lottery_type: int,
    modules: list[dict[str, Any]],
    zodiac_map: dict[str, list[str]],
    color_map: dict[str, list[str]],
    rows_per_module: int,
) -> dict[str, Any]:
    """为单个彩种生成前端页需要的全部模块数据。"""
    # 香港彩最近几期可能混有无效开奖号（例如 "00"），这里放大抓取窗口，
    # 再从有效结果里截最近 10 条，避免前端需要 10 条时被脏数据挤掉。
    draws = get_valid_draws(conn, lottery_type, limit=max(rows_per_module * 8, 50))
    selected_draws = list(reversed(draws[:rows_per_module]))
    if len(selected_draws) < rows_per_module:
        raise ValueError(f"type={lottery_type} 可用历史开奖不足 {rows_per_module} 条")

    module_reports: list[dict[str, Any]] = []
    total_upserts = 0
    total_trimmed = 0

    for module in modules:
        mode_id = int(module["mode_id"])
        table_name = f"mode_payload_{mode_id}"
        upserts = 0
        for draw in selected_draws:
            row_data = build_lightweight_row(
                mode_id=mode_id,
                lottery_type=lottery_type,
                draw=draw,
                zodiac_map=zodiac_map,
                color_map=color_map,
            )
            insert_row(conn, table_name, row_data)
            upserts += 1
        trimmed = trim_created_rows(conn, table_name, lottery_type, rows_per_module)
        module_reports.append({
            "mode_id": mode_id,
            "mechanism_key": str(module["mechanism_key"]),
            "table_name": table_name,
            "rows_written": upserts,
            "rows_kept": created_row_count(conn, table_name, lottery_type),
            "rows_trimmed": trimmed,
            "latest_issue": issue_text(selected_draws[-1]),
        })
        total_upserts += upserts
        total_trimmed += trimmed

    return {
        "lottery_type": lottery_type,
        "draw_count": len(selected_draws),
        "rows_per_module": rows_per_module,
        "modules": module_reports,
        "total_upserts": total_upserts,
        "total_trimmed": total_trimmed,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="快速生成香港彩/澳门彩前端页需要的 created 预测数据。",
    )
    parser.add_argument(
        "--db-target",
        default=DEFAULT_DB_TARGET,
        help="数据库连接串或路径。",
    )
    parser.add_argument(
        "--types",
        nargs="+",
        type=int,
        default=list(SUPPORTED_TYPES),
        help="要处理的彩种 type 列表，默认 1 2。",
    )
    parser.add_argument(
        "--rows-per-module",
        type=int,
        default=ROWS_PER_MODULE,
        help="每个模块保留的最近行数，默认 10。",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    rows_per_module = max(1, int(args.rows_per_module))
    requested_types = [int(item) for item in args.types if int(item) in SUPPORTED_TYPES]
    if not requested_types:
        raise ValueError("至少需要一个受支持的 type（1 或 2）")

    with connect(args.db_target) as conn:
        zodiac_map = load_fixed_map(conn, "生肖")
        color_map = load_fixed_map(conn, "波色")
        modules = load_frontend_modules()

        summary = {
            "db_target": str(args.db_target),
            "rows_per_module": rows_per_module,
            "module_count": len(modules),
            "types": {},
        }

        for lottery_type in requested_types:
            summary["types"][str(lottery_type)] = generate_for_type(
                conn=conn,
                lottery_type=lottery_type,
                modules=modules,
                zodiac_map=zodiac_map,
                color_map=color_map,
                rows_per_module=rows_per_module,
            )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
