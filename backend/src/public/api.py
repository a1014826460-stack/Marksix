"""公开 API — 站点首页数据、最新开奖、公开页面辅助函数。

从 app.py 提取，不改变任何函数签名与行为。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PREDICT_ROOT = Path(__file__).resolve().parents[1] / "predict"
if str(_PREDICT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PREDICT_ROOT))

from db import connect  # noqa: E402
from helpers import (  # noqa: E402
    apply_lottery_draw_overlay, build_draw_result_payload, color_name_to_key,
    load_fixed_data_maps, load_lottery_draw_map, load_mode_payload_rows_from_source,
    merge_preferred_mode_payload_rows, split_csv,
)
from mechanisms import get_prediction_config  # noqa: E402
from admin.prediction import resolve_prediction_table_for_mode  # noqa: E402
from utils.created_prediction_store import (  # noqa: E402
    CREATED_SCHEMA_NAME, created_table_exists, normalize_color_label,
)


def extract_special_result(row: dict[str, Any]) -> dict[str, Any]:
    """从历史记录中提取特码号、生肖和波色，供前端公开页展示开奖号。"""
    codes = split_csv(row.get("res_code"))
    zodiacs = split_csv(row.get("res_sx"))
    colors = split_csv(row.get("res_color"))
    index = len(codes) - 1
    if index < 0:
        return {"code": "", "zodiac": "", "color": ""}
    return {
        "code": codes[index],
        "zodiac": zodiacs[index] if index < len(zodiacs) else "",
        "color": colors[index] if index < len(colors) else "",
    }


def summarize_prediction_text(row: dict[str, Any]) -> str:
    """把不同玩法的历史字段归一成可读文本，避免前端猜测每张源表的结构。"""
    if row.get("content"):
        return str(row["content"])
    xiao_values = [str(row.get("xiao_1") or "").strip(), str(row.get("xiao_2") or "").strip()]
    joined_xiao = " / ".join(value for value in xiao_values if value)
    if joined_xiao:
        return joined_xiao
    for key in ("title", "jiexi", "code", "start", "end"):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def _check_prediction_correct(prediction_text: str, special: dict[str, Any]) -> bool | None:
    """判断预测是否命中特码结果。未开奖时返回 None。"""
    if not special["code"]:
        return None
    targets = [special["zodiac"], special["code"], special["color"]]
    return any(target and target in prediction_text for target in targets)


def serialize_public_history_row(row: dict[str, Any]) -> dict[str, Any]:
    special = extract_special_result(row)
    issue = f"{row.get('year') or ''}{row.get('term') or ''}".strip()
    prediction_text = summarize_prediction_text(row)
    draw_is_opened = row.get("draw_is_opened")
    is_opened = bool(draw_is_opened) if draw_is_opened is not None else bool(special["code"])
    return {
        "issue": issue,
        "year": str(row.get("year") or ""),
        "term": str(row.get("term") or ""),
        "prediction_text": prediction_text,
        "result_text": (f"{special['zodiac']}{special['code']}".strip() if is_opened and special["code"] else "待开奖"),
        "is_opened": is_opened,
        "is_correct": _check_prediction_correct(prediction_text, special) if is_opened else None,
        "source_web_id": row.get("web_id"),
        "raw": row,
    }


def load_public_module_history(
    db_path: str | Path,
    mechanism_key: str,
    history_limit: int,
    *,
    mode_id: int | None = None,
    lottery_type_id: int | None = None,
    web_start: int | None = None,
    web_end: int | None = None,
) -> dict[str, Any]:
    """读取模块现有历史记录，不重新生成预测数据。"""
    config = get_prediction_config(mechanism_key)
    with connect(db_path) as conn:
        rows: list[dict[str, Any]] = []
        history_schema = "public"
        resolved_mode_id = int(mode_id or config.default_modes_id or 0)
        history_table = resolve_prediction_table_for_mode(
            conn,
            resolved_mode_id,
            config.default_table,
        )
        history_sources: list[str] = []
        preferred_limit = max(history_limit * 2, history_limit)

        preferred_rows: list[dict[str, Any]] = []
        if getattr(conn, "engine", "") == "postgres" and created_table_exists(conn, history_table):
            preferred_rows = load_mode_payload_rows_from_source(
                conn,
                table_name=history_table,
                schema_name=CREATED_SCHEMA_NAME,
                limit=preferred_limit,
                lottery_type_id=lottery_type_id,
                web_start=web_start,
                web_end=web_end,
            )
            if preferred_rows:
                history_schema = CREATED_SCHEMA_NAME
                history_sources.append(CREATED_SCHEMA_NAME)

        fallback_rows: list[dict[str, Any]] = []
        if len(preferred_rows) < history_limit and conn.table_exists(history_table):
            fallback_rows = load_mode_payload_rows_from_source(
                conn,
                table_name=history_table,
                limit=max(history_limit * 3, history_limit),
                lottery_type_id=lottery_type_id,
                web_start=web_start,
                web_end=web_end,
            )
            if fallback_rows:
                history_sources.append("public")

        rows = merge_preferred_mode_payload_rows(preferred_rows, fallback_rows, history_limit)
        rows = apply_lottery_draw_overlay(
            conn,
            rows,
            default_lottery_type_id=lottery_type_id,
        )

        if not rows:
            return {
                "mechanism_key": config.key,
                "title": config.title,
                "default_modes_id": resolved_mode_id,
                "default_table": history_table,
                "history_table": history_table,
                "history_schema": history_schema,
                "history_sources": history_sources,
                "history": [],
            }

    return {
        "mechanism_key": config.key,
        "title": config.title,
        "default_modes_id": resolved_mode_id,
        "default_table": history_table,
        "history_table": history_table,
        "history_schema": history_schema,
        "history_sources": history_sources,
        "history": [serialize_public_history_row(row) for row in rows],
    }


def resolve_public_site(db_path: str | Path, site_id: int | None = None, domain: str | None = None) -> dict[str, Any]:
    from admin.crud import get_site as _get_site, public_site as _public_site
    from tables import ensure_admin_tables as _ensure_tables
    _ensure_tables(db_path)
    if site_id is not None:
        return _get_site(db_path, site_id)

    normalized_domain = str(domain or "").strip().lower()
    with connect(db_path) as conn:
        if normalized_domain:
            row = conn.execute(
                """
                SELECT s.*, l.name AS lottery_name
                FROM managed_sites s
                LEFT JOIN lottery_types l ON l.id = s.lottery_type_id
                WHERE LOWER(COALESCE(s.domain, '')) = ?
                  AND s.enabled = 1
                ORDER BY s.id
                LIMIT 1
                """,
                (normalized_domain,),
            ).fetchone()
            if row:
                data = _public_site(row)
                data["enabled"] = bool(data["enabled"])
                return data

        row = conn.execute(
            """
            SELECT s.*, l.name AS lottery_name
            FROM managed_sites s
            LEFT JOIN lottery_types l ON l.id = s.lottery_type_id
            WHERE s.enabled = 1
            ORDER BY s.id
            LIMIT 1
            """
        ).fetchone()
        if not row:
            raise KeyError("未找到可展示的站点配置")
        data = _public_site(row)
        data["enabled"] = bool(data["enabled"])
        return data


def load_public_draw_snapshot(
    db_path: str | Path,
    site: dict[str, Any],
    mechanism_keys: list[str],
) -> dict[str, Any]:
    """公开页最新开奖号码只认 `lottery_draws`，不再从模块历史表反推。"""
    del mechanism_keys

    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT year, term, numbers
            FROM lottery_draws
            WHERE lottery_type_id = ?
              AND is_opened = 1
              AND numbers IS NOT NULL
              AND numbers != ''
            ORDER BY year DESC, term DESC, id DESC
            LIMIT 1
            """,
            (int(site.get("lottery_type_id") or 1),),
        ).fetchone()

        if not row:
            return {
                "current_issue": "",
                "result_balls": [],
                "special_ball": None,
            }

        latest_draw = dict(row)
        zodiac_map, color_map = load_fixed_data_maps(conn)
        draw_result = build_draw_result_payload(
            latest_draw.get("numbers"),
            zodiac_map,
            color_map,
        )
        balls = draw_result["balls"]

    return {
        "current_issue": f"{latest_draw.get('year') or ''}{latest_draw.get('term') or ''}",
        "result_balls": balls[:-1],
        "special_ball": balls[-1] if balls else None,
    }


def get_public_site_page_data(
    db_path: str | Path,
    *,
    site_id: int | None = None,
    domain: str | None = None,
    history_limit: int = 8,
) -> dict[str, Any]:
    """公开页数据按站点模块配置读取历史记录，不在这里主动生成预测。"""
    site = resolve_public_site(db_path, site_id=site_id, domain=domain)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM site_prediction_modules
            WHERE site_id = ?
              AND status = 1
            ORDER BY sort_order, id
            """,
            (int(site["id"]),),
        ).fetchall()

    modules = []
    for row in rows:
        module_meta = load_public_module_history(
            db_path,
            str(row["mechanism_key"]),
            history_limit,
            mode_id=int(row["mode_id"] or 0),
            lottery_type_id=int(site.get("lottery_type_id") or 1),
            web_start=int(site.get("start_web_id") or 0),
            web_end=int(site.get("end_web_id") or 0),
        )
        modules.append(
            {
                "id": int(row["id"]),
                "mechanism_key": str(row["mechanism_key"]),
                "sort_order": int(row["sort_order"] or 0),
                "status": bool(row["status"]),
                **module_meta,
            }
        )

    mechanism_keys = [str(row["mechanism_key"]) for row in rows]

    return {
        "site": site,
        "draw": load_public_draw_snapshot(db_path, site, mechanism_keys),
        "modules": modules,
    }


def get_public_latest_draw(
    db_path: str | Path,
    lottery_type_id: int = 1,
) -> dict[str, Any]:
    """从 lottery_draws 表读取指定彩种的最新开奖数据，返回开奖号码球列表。

    使用 fixed_data 表中的生肖/波色映射将号码转换为前端可渲染的格式。
    """
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT year, term, numbers
            FROM lottery_draws
            WHERE lottery_type_id = ?
              AND is_opened = 1
              AND numbers IS NOT NULL AND numbers != ''
              AND POSITION(',' IN numbers) > 0
            ORDER BY year DESC, term DESC
            LIMIT 1
            """,
            (int(lottery_type_id),),
        ).fetchone()

        if not row:
            return {
                "current_issue": "",
                "result_balls": [],
                "special_ball": None,
            }

        latest_draw = dict(row)
        zodiac_map, color_map = load_fixed_data_maps(conn)
        draw_result = build_draw_result_payload(
            latest_draw.get("numbers"),
            zodiac_map,
            color_map,
        )
        balls = draw_result["balls"]

        return {
            "current_issue": f"{latest_draw['year']}{latest_draw['term']}",
            "result_balls": balls[:-1],
            "special_ball": balls[-1] if balls else None,
        }


# ── /api/public/draw-history ──────────────────────────────

def _build_ball_attributes(
    number: str,
    zodiac_map: dict[str, str],
    color_map: dict[str, str],
    element_map: dict[str, str],
    animal_map: dict[str, str],
    combined_map: dict[str, str],
) -> dict[str, Any]:
    """为单个号码球计算所有展示属性。"""
    try:
        n = int(number)
        code = f"{n:02d}"
    except (ValueError, TypeError):
        return {"value": str(number)}

    zodiac = zodiac_map.get(code, "")
    color = normalize_color_label(color_map.get(code, ""))
    element = element_map.get(code, "")
    wave = color.removesuffix("波") if color else ""

    # 大小
    size = "大" if n >= 25 else "小"

    # 单双
    odd_even = "单" if n % 2 == 1 else "双"

    # 合单双（个位 + 十位之和的奇偶）
    digit_sum = (n // 10) + (n % 10)
    combined = "合单" if digit_sum % 2 == 1 else "合双"

    # 家禽 / 野兽
    animal = animal_map.get(zodiac, "")

    # 总和单双（由调用方汇总后计算）
    return {
        "value": code,
        "color": color_name_to_key(color) if color else "red",
        "zodiac": zodiac,
        "element": element,
        "wave": wave,
        "size": size,
        "oddEven": odd_even,
        "combinedOddEven": combined,
        "animalType": animal,
        "sumOddEven": "",  # 单个球无总和，调用方填充
    }


LOTTERY_NAMES = {1: "香港彩", 2: "澳门彩", 3: "台湾彩"}


def get_draw_history(
    db_path: str | Path,
    lottery_type: int = 3,
    year: int | None = None,
    sort: str = "l",
) -> dict[str, Any]:
    """返回指定彩种、年份的开奖历史列表。

    sort: "l" = 落球顺序（数据库原样），"d" = 号码大小排序
    """
    from datetime import datetime as _dt

    current_year = year or _dt.now().year

    with connect(db_path) as conn:
        # 可用年份
        year_rows = conn.execute(
            """
            SELECT DISTINCT year FROM lottery_draws
            WHERE lottery_type_id = ? AND is_opened = 1
            ORDER BY year DESC
            """,
            (int(lottery_type),),
        ).fetchall()
        years = [int(r["year"]) for r in year_rows]

        # 开奖记录
        rows = conn.execute(
            """
            SELECT year, term, numbers, draw_time
            FROM lottery_draws
            WHERE lottery_type_id = ? AND is_opened = 1 AND year = ?
            ORDER BY year DESC, term DESC, id DESC
            """,
            (int(lottery_type), int(current_year)),
        ).fetchall()

        # 加载映射表
        zodiac_map, color_map = load_fixed_data_maps(conn)
        element_map = _build_number_map(conn, "五行")
        animal_map = _build_zodiac_category_map(conn)
        combined_map = _build_number_map(conn, "合单双")  # unused directly, computed in helper

    items: list[dict[str, Any]] = []
    for row in rows:
        numbers = split_csv(row["numbers"])
        if len(numbers) < 7:
            continue

        # 处理普通球 + 特码球
        balls_data = []
        for num in numbers[:-1]:
            balls_data.append(_build_ball_attributes(
                num, zodiac_map, color_map, element_map, animal_map, combined_map,
            ))
        special_data = _build_ball_attributes(
            numbers[-1], zodiac_map, color_map, element_map, animal_map, combined_map,
        )

        # 排序
        if sort == "d":
            balls_data.sort(key=lambda b: int(b["value"]))
            special_is_min = int(special_data["value"]) <= int(balls_data[0]["value"])

        # 总和单双
        all_nums = [int(b["value"]) for b in balls_data] + [int(special_data["value"])]
        total_sum = sum(all_nums)
        total_odd_even = "单" if total_sum % 2 == 1 else "双"
        for b in balls_data:
            b["sumOddEven"] = total_odd_even
        special_data["sumOddEven"] = total_odd_even

        issue = f"{row['year']}{row['term']}"
        draw_time = str(row.get("draw_time") or "")
        date_str = draw_time[:10] if draw_time else ""
        items.append({
            "issue": str(row["term"]),
            "date": date_str,
            "title": f"{LOTTERY_NAMES.get(lottery_type, '彩种')}开奖记录 {date_str} 第{row['term']}期" if date_str else f"{LOTTERY_NAMES.get(lottery_type, '彩种')}开奖记录 第{row['term']}期",
            "balls": balls_data if sort == "l" or not special_is_min else balls_data,
            "specialBall": special_data,
        })

    return {
        "lottery_type": lottery_type,
        "lottery_name": LOTTERY_NAMES.get(lottery_type, ""),
        "year": current_year,
        "sort": sort,
        "years": years,
        "items": items,
    }


def _build_number_map(conn: Any, sign: str) -> dict[str, str]:
    """构建单号码到分类的映射（如五行、合单双）。"""
    result: dict[str, str] = {}
    if not conn.table_exists("fixed_data"):
        return result
    rows = conn.execute(
        "SELECT name, code FROM fixed_data WHERE sign = ?", (sign,),
    ).fetchall()
    for row in rows:
        label = str(row["name"] or "").strip()
        for code in split_csv(str(row["code"] or "")):
            try:
                normalized = f"{int(code):02d}"
            except ValueError:
                continue
            result[normalized] = label
            result[str(int(normalized))] = label
    return result


def _build_zodiac_category_map(conn: Any) -> dict[str, str]:
    """构建生肖→家禽/野兽映射。"""
    result: dict[str, str] = {}
    if not conn.table_exists("fixed_data"):
        return result
    for sign in ("家禽|野兽", "家野肖"):
        rows = conn.execute(
            "SELECT name, code FROM fixed_data WHERE sign = ?", (sign,),
        ).fetchall()
        for row in rows:
            category = str(row["name"] or "").strip()
            for zodiac in split_csv(str(row["code"] or "")):
                zodiac = zodiac.strip()
                if zodiac:
                    result.setdefault(zodiac, category)
    return result

