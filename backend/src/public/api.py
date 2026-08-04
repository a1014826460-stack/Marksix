"""公开 API — 站点首页数据、最新开奖、公开页面辅助函数。

从 app.py 提取，不改变任何函数签名与行为。
"""
from __future__ import annotations

import logging
import re
from typing import Any

from db import connect
from helpers import (
    apply_lottery_draw_overlay, build_draw_result_payload, color_name_to_key,
    get_effective_next_draw_payload,
    load_fixed_data_maps, load_lottery_draw_map, load_mode_payload_rows_from_source,
    merge_preferred_mode_payload_rows, split_csv,
)
from predict.common import PredictionConfig
from predict.mechanisms import get_prediction_config
from admin.prediction import resolve_prediction_table_for_mode
from utils.created_prediction_store import (
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


def attach_domestic_wild_result_category(
    rows: list[dict[str, Any]],
    zodiac_category_map: dict[str, str],
) -> list[dict[str, Any]]:
    """Attach the fixed-data domestic/wild category of each opened special zodiac."""
    annotated_rows: list[dict[str, Any]] = []
    for row in rows:
        annotated = dict(row)
        special = extract_special_result(annotated)
        category = str(zodiac_category_map.get(special["zodiac"], "") or "").strip()
        if category:
            annotated["domestic_wild_category"] = category
        annotated_rows.append(annotated)
    return annotated_rows


def attach_qinqi_reference(
    rows: list[dict[str, Any]],
    qinqi_value_map: dict[str, tuple[str, ...]],
) -> list[dict[str, Any]]:
    """Attach the fixed-data four-arts legend without changing supplier row fields."""
    top = "　".join(
        f"{label}:{''.join(qinqi_value_map.get(label, ()))}"
        for label in ("琴", "棋")
    )
    bottom = "　".join(
        f"{label}:{''.join(qinqi_value_map.get(label, ()))}"
        for label in ("书", "画")
    )
    reference = "\n".join(part for part in (top, bottom) if part)
    return [{**row, "qinqi_reference": reference} for row in rows]


def _normalize_public_image_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.startswith("/uploads/") or raw.startswith("http://") or raw.startswith("https://"):
        return raw
    normalized = raw.replace("\\", "/")
    match = re.search(r"/data/Images/(.+)$", normalized)
    if match:
        return f"/uploads/{match.group(1)}"
    return raw


def summarize_prediction_text(row: dict[str, Any]) -> str:
    """把不同玩法的历史字段归一成可读文本，避免前端猜测每张源表的结构。"""
    if row.get("content"):
        return str(row["content"])
    jia = str(row.get("jia") or "").strip()
    ye = str(row.get("ye") or "").strip()
    if jia or ye:
        return f"家禽|{jia};野兽|{ye}"
    dx = str(row.get("dx") or "").strip()
    ds = str(row.get("ds") or "").strip()
    if dx or ds:
        return dx or ds
    xiao_values = [str(row.get("xiao_1") or "").strip(), str(row.get("xiao_2") or "").strip()]
    joined_xiao = " / ".join(value for value in xiao_values if value)
    if joined_xiao:
        return joined_xiao
    for key in ("title", "jiexi", "code", "start", "end"):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


# 五行元素映射（与 public.fixed_data 中 "五行肖" sign 一致）
_ELEMENT_MAP: dict[str, str] = {}
_ELEMENT_BY_GROUP = {
    "金": ("10", "11", "22", "23", "34", "35", "46", "47"),
    "木": ("04", "05", "16", "17", "28", "29", "40", "41"),
    "水": ("07", "08", "19", "20", "31", "32", "43", "44"),
    "火": ("01", "02", "13", "14", "25", "26", "37", "38"),
    "土": ("03", "06", "09", "12", "15", "18", "21", "24", "27", "30", "33", "36", "39", "42", "45", "48"),
}
for _el, _codes in _ELEMENT_BY_GROUP.items():
    for _c in _codes:
        _ELEMENT_MAP[_c] = _el


def _compute_outcome_from_row(row: dict[str, Any]) -> str:
    """从行数据计算所有可能的特码分类标签，供 hit_checker 使用。

    输出为 `|` 分隔的标签串，覆盖单双、大小、头、尾、波色、合数单双、
    合数大小、家禽野兽、特码生肖、号码、以及五行元素。
    """
    codes = split_csv(row.get("res_code"))
    zodiacs = split_csv(row.get("res_sx"))
    colors = split_csv(row.get("res_color"))
    if not codes:
        return ""
    code = codes[-1]
    zodiac = zodiacs[-1] if zodiacs else ""
    color = colors[-1].lower() if colors else ""
    number = int(code)
    digit_sum = number // 10 + number % 10

    domestic = {"牛", "狗", "猪", "羊", "马", "鸡"}
    wave_map = {"red": "红波", "blue": "蓝波", "green": "绿波"}
    # 五行元素映射（与 public.fixed_data 中 "五行肖" sign 一致）
    element = _ELEMENT_MAP.get(code, "")
    # 琴棋书画映射
    _QQSH_ZODIAC_MAP = {
        "兔": "琴", "蛇": "琴", "鸡": "琴",
        "鼠": "棋", "牛": "棋", "狗": "棋",
        "虎": "书", "龙": "书", "马": "书",
        "羊": "画", "猴": "画", "猪": "画",
    }
    qqsh_label = _QQSH_ZODIAC_MAP.get(zodiac, "")
    outcomes = [
        "单数" if number % 2 == 1 else "双数",
        "大数" if number >= 25 else "小数",
        "单" if number % 2 == 1 else "双",
        "大" if number >= 25 else "小",
        f"{number // 10}头",
        ("0头" if number < 10 else f"{number // 10}头") + ("双" if number % 2 == 0 else "单"),
        f"{number % 10}尾",
        f"{number % 10}",
        wave_map.get(color, ""),
        "合单" if digit_sum % 2 == 1 else "合双",
        "合数大" if digit_sum >= 7 else "合数小",
        "家禽" if zodiac in domestic else "野兽",
        zodiac,
        code,
        element,
        qqsh_label,
    ]
    return "|".join(o for o in outcomes if o)


def _check_correct_by_mechanism(
    prediction_text: str, row: dict[str, Any], config: "PredictionConfig"
) -> bool | None:
    """用机制专属的 hit_checker 判断预测是否正确。

    _compute_outcome_from_row 返回 ``|`` 分隔的复合标签串（单双/大小/头/尾/
    波色/合数/家禽野兽/生肖/号码），而 content_parser 提取的是单个维度标签。
    标准 contains_hit/excludes_hit 做的是单值精确匹配，因此需要逐标签检查而非
    把整串复合 outcome 直接传给 hit_checker。
    """
    from predict.common import contains_hit as _std_contains, excludes_hit as _std_excludes

    special = extract_special_result(row)
    if not special["code"]:
        return None
    outcome = _compute_outcome_from_row(row)
    content_labels = config.content_parser(prediction_text)
    if not content_labels:
        return None
    # 标准命中检查：复合 outcome 中包含预测标签即为命中
    if config.hit_checker is _std_contains:
        return any(label in outcome for label in content_labels)
    # 标准绝杀检查：复合 outcome 中不包含任何预测标签即为命中
    if config.hit_checker is _std_excludes:
        return not any(label in outcome for label in content_labels)
    # 自定义 hit_checker（如 mixed_dimension_*）自己处理复合 outcome
    return config.hit_checker(outcome, content_labels)


def serialize_public_history_row(
    row: dict[str, Any],
    config: "PredictionConfig | None" = None,
) -> dict[str, Any]:
    special = extract_special_result(row)
    issue = f"{row.get('year') or ''}{row.get('term') or ''}".strip()
    prediction_text = summarize_prediction_text(row)
    draw_is_opened = row.get("draw_is_opened")
    is_opened = bool(draw_is_opened) if draw_is_opened is not None else bool(special["code"])
    is_correct = None
    if is_opened and special["code"]:
        if config is not None:
            # 用机制的 content_loader 提取正确的预测来源字段
            # （例如天地生肖用 xiao 列而非 content 列）
            try:
                check_text = config.content_loader(row)
            except Exception:
                check_text = ""
            # 回退：content_loader 返回空时（如逢买必中 ds 列），用 prediction_text
            if not check_text:
                check_text = prediction_text
            is_correct = _check_correct_by_mechanism(check_text, row, config)
        else:
            # 兜底：简单字符串匹配（含 xiao 列增强）
            check_text = prediction_text
            xiao = str(row.get("xiao") or "").strip()
            if xiao:
                check_text = check_text + "," + xiao
            targets = [special["zodiac"], special["code"], special["color"]]
            is_correct = any(target and target in check_text for target in targets)
    return {
        "issue": issue,
        "year": str(row.get("year") or ""),
        "term": str(row.get("term") or ""),
        "prediction_text": prediction_text,
        "image_url": _normalize_public_image_url(row.get("image_url")),
        "result_text": (f"{special['zodiac']}{special['code']}".strip() if is_opened and special["code"] else "待开奖"),
        "is_opened": is_opened,
        "is_correct": is_correct,
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
        # Generated rows may contain several records for the same issue. Read a
        # bounded wider window before merging so deduplication can still supply
        # the requested number of distinct periods.
        source_limit = max(history_limit * 20, 100)

        preferred_rows: list[dict[str, Any]] = []
        if getattr(conn, "engine", "") == "postgres" and created_table_exists(conn, history_table):
            preferred_rows = load_mode_payload_rows_from_source(
                conn,
                table_name=history_table,
                schema_name=CREATED_SCHEMA_NAME,
                limit=source_limit,
                lottery_type_id=lottery_type_id,
                web_start=web_start,
                web_end=web_end,
            )
            if preferred_rows:
                history_schema = CREATED_SCHEMA_NAME
                history_sources.append(CREATED_SCHEMA_NAME)

        fallback_rows: list[dict[str, Any]] = []
        preferred_unique_rows = merge_preferred_mode_payload_rows(
            preferred_rows,
            [],
            history_limit,
        )
        if len(preferred_unique_rows) < history_limit and conn.table_exists(history_table):
            fallback_rows = load_mode_payload_rows_from_source(
                conn,
                table_name=history_table,
                limit=source_limit,
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
        if config.key == "title_14":
            rows = attach_domestic_wild_result_category(
                rows,
                _build_zodiac_category_map(conn),
            )
        if config.key == "qinqi":
            qinqi_map = {
                str(row["name"] or "").strip(): tuple(split_csv(str(row["code"] or "")))
                for row in conn.execute(
                    "SELECT name, code FROM fixed_data WHERE sign = ?",
                    ("四艺生肖",),
                ).fetchall()
            } if conn.table_exists("fixed_data") else {}
            rows = attach_qinqi_reference(rows, qinqi_map)

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
        "history": [serialize_public_history_row(row, config) for row in rows],
    }


def resolve_public_site(db_path: str | Path, site_id: int | None = None, domain: str | None = None) -> dict[str, Any]:
    from domains.sites.service import get_site as _get_site, public_site as _public_site
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
            SELECT year, term, numbers, draw_time
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
    lottery_type_id: int | None = None,
    mode_ids: list[int] | None = None,
    history_web_start: int | None = None,
    history_web_end: int | None = None,
) -> dict[str, Any]:
    """公开页数据按站点模块配置读取历史记录，不在这里主动生成预测。"""
    site = resolve_public_site(db_path, site_id=site_id, domain=domain)
    effective_lottery_type_id = int(lottery_type_id or site.get("lottery_type_id") or 1)
    site = {**site, "lottery_type_id": effective_lottery_type_id}
    logger = logging.getLogger("public.site_page")
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

    allowed_mode_ids = {
        int(mode_id)
        for mode_id in (mode_ids or [])
        if isinstance(mode_id, int) and mode_id > 0
    }
    if allowed_mode_ids:
        rows = [row for row in rows if int(row["mode_id"] or 0) in allowed_mode_ids]

    modules = []
    for row in rows:
        mechanism_key = str(row["mechanism_key"])
        try:
            module_meta = load_public_module_history(
                db_path,
                mechanism_key,
                history_limit,
                mode_id=int(row["mode_id"] or 0),
                lottery_type_id=effective_lottery_type_id,
                web_start=(history_web_start if history_web_start is not None else int(site.get("web_id") or 0)),
                web_end=(history_web_end if history_web_end is not None else int(site.get("web_id") or 0)),
            )
        except Exception as exc:
            logger.warning(
                "skip public module site_id=%s mechanism_key=%s mode_id=%s error=%s",
                site.get("id"),
                mechanism_key,
                row.get("mode_id"),
                exc,
            )
            continue
        if int(module_meta.get("default_modes_id") or 0) in {474, 475, 476, 478}:
            history_rows = list(module_meta.get("history") or [])
            if history_rows:
                history_rows[0]["image_url"] = _normalize_public_image_url(history_rows[0].get("image_url"))
                for extra_row in history_rows[1:]:
                    extra_row["image_url"] = ""
                module_meta["history"] = history_rows
        modules.append(
            {
                "id": int(row["id"]),
                "mechanism_key": mechanism_key,
                "sort_order": int(row["sort_order"] or 0),
                "status": bool(row["status"]),
                **module_meta,
            }
        )

    mechanism_keys = [str(row["mechanism_key"]) for row in modules]

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
            SELECT year, term, numbers, draw_time
            FROM lottery_draws
            WHERE lottery_type_id = ?
              AND is_opened = 1
              AND numbers IS NOT NULL AND numbers != ''
            ORDER BY year DESC, term DESC
            LIMIT 1
            """,
            (int(lottery_type_id),),
        ).fetchone()

        if not row:
            return {
                "current_issue": "",
                "draw_time": "",
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
            "draw_time": str(latest_draw.get("draw_time") or ""),
            "result_balls": balls[:-1],
            "special_ball": balls[-1] if balls else None,
        }


def get_public_next_draw_deadline(
    db_path: str | Path,
    lottery_type_id: int = 3,
) -> dict[str, Any]:
    """Return next draw time derived from the latest opened issue only."""
    with connect(db_path) as conn:
        payload = get_effective_next_draw_payload(conn, int(lottery_type_id))
        return {
            "current_issue": payload.get("current_issue") or "",
            "next_issue": payload.get("next_issue") or "",
            "next_time": payload.get("next_time"),
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
    """构建单号码到分类的映射（如五行、合单双）。
    params:
        - sign: fixed_data表中的分类标识，如“五行”、“合单双”等。
        - conn: 数据库连接对象，必须具有 table_exists 和 execute 方法。
    returns:
        - dict[str, str]: 号码（两位字符串）到分类标签的映射，以及号码（整数形式）到分类标签的映射。
    """
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
    """构建生肖→家禽/野兽映射。
    params:
    - conn: 数据库连接对象，必须具有 table_exists 和 execute 方法。
    returns:
    - dict[str, str]: 生肖名称到家禽/野兽分类的映射。
    """
    result: dict[str, str] = {}
    if not conn.table_exists("fixed_data"):
        return result
    for sign in ("家禽|野兽", "家野肖"):
        rows = conn.execute(
            "SELECT name, code FROM fixed_data WHERE sign = ?", (sign,),
        ).fetchall()
        for row in rows:
            category = {"家肖": "家禽", "野肖": "野兽"}.get(
                str(row["name"] or "").strip(),
                str(row["name"] or "").strip(),
            )
            for zodiac in split_csv(str(row["code"] or "")):
                zodiac = zodiac.strip()
                if zodiac:
                    result.setdefault(zodiac, category)
    return result


# ── /api/public/current-period ──────────────────────────────


def get_current_period(
    db_path: str | Path,
    lottery_type_id: int = 3,
) -> dict[str, Any]:
    """返回指定彩种的当前已开奖期号与年份。

    数据来源：lottery_draws 表中最新的 is_opened=1 记录。
    """
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT year, term
            FROM lottery_draws
            WHERE lottery_type_id = ?
              AND is_opened = 1
            ORDER BY year DESC, term DESC
            LIMIT 1
            """,
            (int(lottery_type_id),),
        ).fetchone()

        if not row:
            return {
                "lottery_type_id": int(lottery_type_id),
                "lottery_name": LOTTERY_NAMES.get(int(lottery_type_id), str(lottery_type_id)),
                "current_period": "",
                "current_year": 0,
                "current_term": 0,
            }

        year = int(row["year"] or 0)
        term = int(row["term"] or 0)
        return {
            "lottery_type_id": int(lottery_type_id),
            "lottery_name": LOTTERY_NAMES.get(int(lottery_type_id), str(lottery_type_id)),
            "current_period": f"{year}{term:03d}",
            "current_year": year,
            "current_term": term,
        }

