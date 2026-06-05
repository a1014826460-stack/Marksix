"""预测资料批量生成服务。

编排站点预测模块的批量生成流程：
站点上下文解析 → 模块加载 → 期号范围加载 → 逐模块逐期生成 → 持久化。
"""

from __future__ import annotations

import hashlib as _hashlib
import json as _json
import logging
import random as _random
import re as _re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from db import connect
from helpers import load_fixed_data_maps
from predict.common import (
    PredictionConfig,
    contains_hit,
    default_content_from_row,
    parse_pipe_label_content,
    parse_zodiac_content,
    predict,
    special_zodiac_from_number_map,
)
from predict.mechanisms import (
    TEXT_HISTORY_MAPPING_TABLE,
    _text_history_row_payload,
    ensure_prediction_configs_loaded,
    format_zodiac_two_codes,
    get_prediction_config,
    list_prediction_configs,
)
from predict.number_maps import SIZE_NUMBER_MAP
from prediction_generation.brain_teaser import (
    build_brain_teaser_generated_content,
    format_brain_teaser_issue_text,
    load_brain_teaser_record_for_issue,
    load_previous_brain_teaser_record_for_issue,
)
from prediction_generation.brain_teaser_image import (
    DEFAULT_OUTPUT_DIR as MODE_475_OUTPUT_DIR,
    DEFAULT_OUTPUT_NAME_TEMPLATE as MODE_475_OUTPUT_NAME_TEMPLATE,
    render_brain_teaser_image,
)
from prediction_generation.mode_474_image import (
    MODE_474_ID,
    build_mode_474_title,
    render_mode_474_prediction_image,
)
from prediction_generation.mode_476_image import (
    MODE_476_ID,
    MODE_476_TITLE,
    render_mode_476_prediction_image,
)
from prediction_generation.mode_478_image import (
    MODE_478_ID,
    MODE_478_TITLE,
    render_mode_478_prediction_image,
)
from prediction_generation.diversity import enforce_prediction_diversity
from runtime_config import get_config_from_conn
from utils.created_prediction_store import (
    CREATED_SCHEMA_NAME,
    find_existing_created_row,
    normalize_color_label,
    table_column_names,
    upsert_created_prediction_row,
)

_logger = logging.getLogger("prediction.service")
_task_logger = logging.getLogger("prediction.task")
_MODE_331_ZODIAC_ORDER = ("鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪")
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_MODE_476_FALLBACK_CONFIG = PredictionConfig(
    key="mode476_fallback",
    title=MODE_476_TITLE,
    default_table="mode_payload_22",
    default_modes_id=22,
    labels=_MODE_331_ZODIAC_ORDER,
    label_count=7,
    outcome_loader=special_zodiac_from_number_map,
    content_loader=default_content_from_row,
    content_parser=parse_pipe_label_content,
    content_formatter=format_zodiac_two_codes,
    hit_checker=contains_hit,
    explanation=(
        "跑马图解（带图）复用跑马图解 7 肖 14 码结构。",
        "当动态机制 title_22 未加载时，使用内置兜底配置保证后台可生成。",
    ),
)
_MODE_478_FALLBACK_CONFIG = PredictionConfig(
    key="mode478_fallback",
    title=MODE_478_TITLE,
    default_table="mode_payload_22",
    default_modes_id=22,
    labels=_MODE_331_ZODIAC_ORDER,
    label_count=7,
    outcome_loader=special_zodiac_from_number_map,
    content_loader=default_content_from_row,
    content_parser=parse_pipe_label_content,
    content_formatter=format_zodiac_two_codes,
    hit_checker=contains_hit,
    explanation=(
        "台湾跑马图（带图）复用跑马图解 7 肖 14 码结构。",
        "当动态机制 title_22 未加载时，使用内置兜底配置保证后台可生成。",
    ),
)


def _resolve_prediction_config_with_mode_fallback(
    mechanism_key: str,
    mode_id: int,
    db_path: str | Path | None = None,
) -> tuple[PredictionConfig, str, bool]:
    normalized_key = str(mechanism_key or "").strip()
    try:
        return get_prediction_config(normalized_key), normalized_key, False
    except Exception:
        pass

    for item in list_prediction_configs(db_path):
        try:
            if int(item.get("default_modes_id") or 0) != int(mode_id or 0):
                continue
        except (TypeError, ValueError):
            continue

        fallback_key = str(item.get("key") or "").strip()
        if not fallback_key:
            continue
        return get_prediction_config(fallback_key), fallback_key, True

    return get_prediction_config(normalized_key), normalized_key, False


# ── 配置读取 ────────────────────────────────────────────


def _default_target_hit_rate(conn: Any) -> float:
    return float(get_config_from_conn(conn, "prediction.default_target_hit_rate", 0.65))


def _max_terms_per_year(conn: Any) -> int:
    return int(get_config_from_conn(conn, "prediction.max_terms_per_year", 365))


# ── 工具函数 ────────────────────────────────────────────


def compute_result_fields(numbers_str: str, zodiac_map: dict, color_map: dict) -> tuple[str, str]:
    res_sx_parts: list[str] = []
    res_color_parts: list[str] = []
    for num_str in (numbers_str or "").split(","):
        raw_num = num_str.strip()
        if not raw_num:
            continue
        try:
            num_zf = f"{int(raw_num):02d}"
        except ValueError:
            continue
        res_sx_parts.append(str(zodiac_map.get(num_zf) or ""))
        res_color_parts.append(normalize_color_label(color_map.get(num_zf, "")))
    return (
        ",".join(res_sx_parts) if any(res_sx_parts) else "",
        ",".join(res_color_parts) if any(res_color_parts) else "",
    )


def compute_next_issue(year: int, term: int, offset: int, *, max_terms_per_year: int = 365) -> tuple[int, int]:
    new_term = term + offset
    new_year = year
    while new_term > max_terms_per_year:
        new_term -= max_terms_per_year
        new_year += 1
    return new_year, new_term


def _make_seed_int(seed_str: str) -> int:
    """从种子字符串生成 32 位整数种子。"""
    return int(_hashlib.sha256(seed_str.encode()).hexdigest(), 16) % (2**32)


def _normalize_prediction_numbers(values: list[Any] | tuple[Any, ...] | None) -> list[str]:
    """Normalize prediction labels into unique two-digit codes."""
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values or ():
        text = str(value or "").strip()
        if not _re.fullmatch(r"\d{1,2}", text):
            continue
        number = int(text)
        if number < 1 or number > 49:
            continue
        code = f"{number:02d}"
        if code in seen:
            continue
        seen.add(code)
        normalized.append(code)
    return normalized


def _build_mode_331_x7m14(
    predicted_labels: list[Any] | tuple[Any, ...] | None,
    zodiac_map: dict[str, str],
    seed_key: str,
) -> str:
    """Build the persisted x7m14 payload for mode_id=331."""
    rng = _random.Random(_make_seed_int(seed_key))
    zodiac_number_map: dict[str, list[str]] = {zodiac: [] for zodiac in _MODE_331_ZODIAC_ORDER}
    for raw_number, raw_zodiac in zodiac_map.items():
        zodiac = str(raw_zodiac or "").strip()
        text = str(raw_number or "").strip()
        if zodiac not in zodiac_number_map or not _re.fullmatch(r"\d{1,2}", text):
            continue
        code = f"{int(text):02d}"
        if code not in zodiac_number_map[zodiac]:
            zodiac_number_map[zodiac].append(code)

    predicted_numbers = _normalize_prediction_numbers(predicted_labels)
    predicted_by_zodiac: dict[str, list[str]] = {}
    for code in predicted_numbers:
        zodiac = str(zodiac_map.get(code) or "").strip()
        if zodiac not in zodiac_number_map:
            continue
        predicted_by_zodiac.setdefault(zodiac, [])
        if code not in predicted_by_zodiac[zodiac]:
            predicted_by_zodiac[zodiac].append(code)

    groups: list[tuple[str, list[str]]] = []
    used_zodiacs: set[str] = set()
    used_numbers: set[str] = set()

    preferred_zodiacs = list(predicted_by_zodiac.keys())
    rng.shuffle(preferred_zodiacs)
    for zodiac in preferred_zodiacs:
        pair: list[str] = []
        predicted_pool = list(predicted_by_zodiac[zodiac])
        rng.shuffle(predicted_pool)
        for code in predicted_pool:
            if code in used_numbers:
                continue
            pair.append(code)
            used_numbers.add(code)
            if len(pair) == 2:
                break

        available_pool = [code for code in zodiac_number_map[zodiac] if code not in used_numbers]
        rng.shuffle(available_pool)
        while len(pair) < 2 and available_pool:
            code = available_pool.pop()
            pair.append(code)
            used_numbers.add(code)

        if len(pair) != 2:
            continue
        groups.append((zodiac, pair))
        used_zodiacs.add(zodiac)
        if len(groups) == 7:
            break

    remaining_zodiacs = [
        zodiac for zodiac in _MODE_331_ZODIAC_ORDER
        if zodiac not in used_zodiacs and len(zodiac_number_map[zodiac]) >= 2
    ]
    rng.shuffle(remaining_zodiacs)
    for zodiac in remaining_zodiacs:
        available_pool = [code for code in zodiac_number_map[zodiac] if code not in used_numbers]
        if len(available_pool) < 2:
            available_pool = list(zodiac_number_map[zodiac])
        if len(available_pool) < 2:
            continue
        pair = rng.sample(available_pool, 2)
        groups.append((zodiac, pair))
        used_zodiacs.add(zodiac)
        used_numbers.update(pair)
        if len(groups) == 7:
            break

    if len(groups) < 7:
        fallback_zodiacs = [zodiac for zodiac in _MODE_331_ZODIAC_ORDER if zodiac not in used_zodiacs]
        if len(fallback_zodiacs) < 7 - len(groups):
            fallback_zodiacs.extend(list(_MODE_331_ZODIAC_ORDER))
        rng.shuffle(fallback_zodiacs)
        global_pool = [f"{number:02d}" for number in range(1, 50)]
        for zodiac in fallback_zodiacs:
            if len(groups) == 7:
                break
            pool = list(zodiac_number_map.get(zodiac) or [])
            if len(pool) < 2:
                pool = list(global_pool)
            if len(pool) < 2:
                continue
            pair = rng.sample(pool, 2)
            groups.append((zodiac, pair))
            used_zodiacs.add(zodiac)

    rng.shuffle(groups)
    payload = [f"{zodiac}|{pair[0]},{pair[1]}" for zodiac, pair in groups[:7]]
    return _json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _ensure_mode_251_xiao(row_data: dict[str, Any], content: Any) -> dict[str, Any]:
    """Backfill mode 251 `xiao` from generated payload when the formatter did not provide it."""
    normalized = dict(row_data)
    if str(normalized.get("xiao") or "").strip():
        return normalized

    labels: list[str] = []
    if isinstance(content, dict):
        if str(content.get("xiao") or "").strip():
            labels.extend(parse_zodiac_content(str(content.get("xiao") or "")))
        # 兼容 title 作为 content 替代列（如 mode_payload_251）
        if not labels:
            raw = str(content.get("content") or content.get("title") or "")
            if raw.strip():
                labels.extend(parse_pipe_label_content(raw))
    else:
        labels.extend(parse_pipe_label_content(str(content or "")))

    deduped: list[str] = []
    for label in labels:
        text = str(label or "").strip()
        if text and text not in deduped:
            deduped.append(text)

    if deduped:
        normalized["xiao"] = ",".join(deduped)
    return normalized


# ── 期号与开奖数据加载 ──────────────────────────────────


def list_opened_draws_in_issue_range(
    conn: Any,
    lottery_type_id: int,
    start_issue: tuple[int, int],
    end_issue: tuple[int, int],
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT year, term, numbers
        FROM lottery_draws
        WHERE lottery_type_id = ?
          AND is_opened = 1
        ORDER BY year ASC, term ASC, id ASC
        """,
        (int(lottery_type_id),),
    ).fetchall()

    draws: list[dict[str, Any]] = []
    for row in rows:
        year = int(row["year"] or 0)
        term = int(row["term"] or 0)
        current = (year, term)
        if current < start_issue or current > end_issue:
            continue

        normalized_numbers: list[str] = []
        for raw_number in str(row["numbers"] or "").split(","):
            text = raw_number.strip()
            if not text:
                continue
            try:
                normalized_numbers.append(f"{int(text):02d}")
            except (TypeError, ValueError):
                continue
        if len(normalized_numbers) < 7:
            continue

        draws.append({
            "year": year,
            "term": term,
            "numbers_str": ",".join(normalized_numbers),
        })
    return draws


def find_latest_opened_draw_before_issue(
    conn: Any,
    lottery_type_id: int,
    target_issue: tuple[int, int],
) -> dict[str, Any] | None:
    rows = conn.execute(
        """
        SELECT year, term, numbers
        FROM lottery_draws
        WHERE lottery_type_id = ?
          AND is_opened = 1
        ORDER BY year DESC, term DESC, id DESC
        """,
        (int(lottery_type_id),),
    ).fetchall()

    for row in rows:
        year = int(row["year"] or 0)
        term = int(row["term"] or 0)
        if (year, term) >= target_issue:
            continue

        normalized_numbers: list[str] = []
        for raw_number in str(row["numbers"] or "").split(","):
            text = raw_number.strip()
            if not text:
                continue
            try:
                normalized_numbers.append(f"{int(text):02d}")
            except (TypeError, ValueError):
                continue
        if len(normalized_numbers) < 7:
            continue

        return {"year": year, "term": term, "numbers_str": ",".join(normalized_numbers)}
    return None


def _load_previous_opened_numbers_for_issue(
    conn: Any,
    *,
    lottery_type_id: int,
    year: int,
    term: int,
) -> str | None:
    previous_draw = find_latest_opened_draw_before_issue(
        conn,
        lottery_type_id=int(lottery_type_id),
        target_issue=(int(year), int(term)),
    )
    if not previous_draw:
        return None
    numbers_str = str(previous_draw.get("numbers_str") or "").strip()
    return numbers_str or None


def _build_future_draws(
    draws: list[dict[str, Any]],
    future_periods: int,
    start_issue: tuple[int, int],
    end_issue: tuple[int, int],
    future_only: bool,
    max_terms_per_year: int,
) -> list[dict[str, Any]]:
    """根据已开奖期号推算未来期号列表。"""
    if int(future_periods or 0) <= 0:
        return []

    latest = draws[-1]
    generated: list[dict[str, Any]] = []
    for offset in range(1, int(future_periods) + 1):
        next_year, next_term = compute_next_issue(
            latest["year"], latest["term"], offset,
            max_terms_per_year=max_terms_per_year,
        )
        generated.append({
            "year": next_year,
            "term": next_term,
            "numbers_str": "",
            "_future": True,
        })

    if future_only:
        return [
            d for d in generated
            if start_issue <= (d["year"], d["term"]) <= end_issue
        ]
    return generated


def _build_safety_draw_map(conn: Any, lottery_type: int) -> dict[tuple[int, int], bool]:
    """构建未开奖期号的安全映射（仅对 type=3）。"""
    safety: dict[tuple[int, int], bool] = {}
    if int(lottery_type) != 3:
        return safety
    rows = conn.execute(
        """
        SELECT year, term, is_opened FROM lottery_draws
        WHERE lottery_type_id = ? AND is_opened = 0
        """,
        (int(lottery_type),),
    ).fetchall()
    for row in rows:
        safety[(int(row["year"]), int(row["term"]))] = True
    return safety


# ── 站点上下文解析 ──────────────────────────────────────


def _resolve_generation_context(db_path: str | Path, site_id: int) -> tuple[int, str]:
    """解析站点 web_id 和名称，校验 web_id 有效性。

    Returns:
        (site_web_id, site_name)
    """
    from domains.sites.service import get_site

    site = get_site(db_path, site_id)
    site_web_id = int(site.get("web_id") or 0)
    if site_web_id <= 0:
        raise ValueError(f"site_id={site_id} 缺少有效 web_id")
    return site_web_id, str(site.get("name") or "")


# ── 最近行加载（多样性用）────────────────────────────────


def _load_recent_rows(
    conn: Any,
    table_name: str,
    lottery_type: int,
    site_web_id: int,
    mode_id: int,
) -> list[dict[str, Any]]:
    """加载指定模式最近已持久化的行，用于跨期多样性校验。"""
    try:
        created_columns = set(table_column_names(conn, CREATED_SCHEMA_NAME, table_name))
        if "content" not in created_columns:
            return []
        created_table = f"{CREATED_SCHEMA_NAME}.{table_name}"
        selected_columns = [column for column in ("title", "content", "jiexi") if column in created_columns]
        if not selected_columns:
            return []
        existing = conn.execute(
            f"SELECT {', '.join(selected_columns)} FROM {created_table} "
            f"WHERE type = ? AND web = ? AND modes_id = ? "
            f"ORDER BY year DESC, term DESC LIMIT 10",
            (str(lottery_type), str(site_web_id), mode_id),
        ).fetchall()
        return [{column: row[column] for column in selected_columns} for row in existing]
    except Exception:
        conn.rollback()
        return []


# ── 单期行生成（按 mode_id 分发）────────────────────────


def _text_prediction_signature(row_like: dict[str, Any] | None) -> tuple[str, str, str] | None:
    if not row_like:
        return None
    signature = tuple(str(row_like.get(key) or "").strip() for key in ("title", "content", "jiexi"))
    return signature if any(signature) else None


def _load_text_history_candidate_payloads(conn: Any, mode_id: int) -> list[dict[str, Any]]:
    if mode_id <= 0 or not conn.table_exists(TEXT_HISTORY_MAPPING_TABLE):
        return []

    columns = set(conn.table_columns(TEXT_HISTORY_MAPPING_TABLE))
    mode_column = "mode_id" if "mode_id" in columns else ("modes_id" if "modes_id" in columns else "")
    if not mode_column:
        return []

    rows = conn.execute(
        f"""
        SELECT *
        FROM {TEXT_HISTORY_MAPPING_TABLE}
        WHERE {mode_column} = ?
        ORDER BY RANDOM()
        LIMIT 50
        """,
        (int(mode_id),),
    ).fetchall()
    return [
        payload for payload in (_text_history_row_payload(row) for row in rows)
        if _text_prediction_signature(payload)
    ]


def _repair_text_prediction_diversity(
    conn: Any,
    *,
    mode_id: int,
    row_data: dict[str, Any],
    recent_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Ensure adjacent text predictions are not fully identical."""
    result = dict(row_data)
    current_signature = _text_prediction_signature(result)
    if not current_signature:
        return result

    recent_signature = None
    for recent_row in recent_rows or []:
        recent_signature = _text_prediction_signature(recent_row)
        if recent_signature:
            break
    if not recent_signature or current_signature != recent_signature:
        return result

    for payload in _load_text_history_candidate_payloads(conn, mode_id):
        candidate = dict(result)
        for key in ("title", "content", "jiexi"):
            if payload.get(key) not in (None, ""):
                candidate[key] = payload[key]
        candidate_signature = _text_prediction_signature(candidate)
        if not candidate_signature:
            continue
        if candidate_signature in {current_signature, recent_signature}:
            continue
        return candidate

    result["_diversity_warning"] = (
        f"mode_id={mode_id}: unable to find alternative text payload; "
        f"adjacent signature remains duplicated"
    )
    return result


def _resolve_safe_res_code(draw: dict[str, Any], draw_key: tuple, safety_map: dict) -> str | None:
    """解析安全开奖号码：若该期尚未开奖则返回 None，避免注入真实 res_code。"""
    if draw_key in safety_map:
        return None
    return draw["numbers_str"]


def _generate_mode_65_row(
    draw: dict[str, Any],
    is_future: bool,
    lottery_type: int,
    site_web_id: int,
    build_row: Any,
) -> dict[str, Any]:
    """mode_id=65：根据特码范围生成分组号码。"""
    if is_future:
        seed_int = _make_seed_int(f"{draw['year']}{draw['term']:03d}")
        _random.seed(seed_int)
        special_code = _random.randint(1, 49)
    else:
        numbers = [n.strip() for n in draw["numbers_str"].split(",") if n.strip()]
        try:
            special_code = int(numbers[-1]) if numbers else 0
        except (ValueError, IndexError):
            special_code = 0

    if special_code <= 12:
        content = ",".join(f"{i:02d}" for i in range(1, 13))
    elif special_code <= 24:
        content = ",".join(f"{i:02d}" for i in range(13, 25))
    elif special_code <= 36:
        content = ",".join(f"{i:02d}" for i in range(25, 37))
    else:
        content = ",".join(f"{i:02d}" for i in range(37, 50))

    return build_row(
        mode_id=65, lottery_type=str(lottery_type),
        year=str(draw["year"]), term=str(draw["term"]),
        web_value=str(site_web_id),
        res_code=_resolve_safe_res_code(draw, (draw["year"], draw["term"]), {}) or "",
        generated_content=content,
    )


def _generate_mode_108_row(
    draw: dict[str, Any],
    is_future: bool,
    safe_res_code: str | None,
    lottery_type: int,
    site_web_id: int,
    config: Any,
    table_name: str,
    db_path: str | Path,
    default_target_hit_rate: float,
    build_row: Any,
) -> dict[str, Any]:
    """mode_id=108：大小中特带1头。"""
    if is_future:
        result = predict(
            config=config, res_code=None, source_table=table_name,
            db_path=db_path, target_hit_rate=default_target_hit_rate,
            random_seed=f"{draw['year']}{draw['term']:03d}",
        )
        predicted_size = str(result["prediction"]["labels"][0])
        seed_int = _make_seed_int(f"{draw['year']}{draw['term']:03d}")
        _random.seed(seed_int)
        size_numbers = SIZE_NUMBER_MAP.get(predicted_size, [])
        chosen_number = _random.choice(size_numbers) if size_numbers else "00"
    else:
        numbers = [n.strip() for n in (safe_res_code or "").split(",") if n.strip()]
        try:
            special_code = int(numbers[-1]) if numbers else 0
        except (ValueError, IndexError):
            special_code = 0
        chosen_number = f"{special_code:02d}"
        predicted_size = "大" if special_code >= 25 else "小"

    num_val = int(chosen_number) if chosen_number.lstrip("0") else 0
    if 10 <= num_val <= 19:
        head_text = "1头"
    elif 20 <= num_val <= 29:
        head_text = "2头"
    elif 30 <= num_val <= 39:
        head_text = "3头"
    elif 40 <= num_val <= 49:
        head_text = "4头"
    else:
        head_text = "0头"

    return build_row(
        mode_id=108, lottery_type=str(lottery_type),
        year=str(draw["year"]), term=str(draw["term"]),
        web_value=str(site_web_id), res_code=safe_res_code or "",
        generated_content={
            "content": [f"{predicted_size}|{chosen_number}"],
            "tou": [head_text],
        },
    )


def _generate_mode_246_row(
    draw: dict[str, Any],
    is_future: bool,
    safe_res_code: str | None,
    lottery_type: int,
    site_web_id: int,
    config: Any,
    table_name: str,
    db_path: str | Path,
    default_target_hit_rate: float,
    zodiac_map: dict,
    build_row: Any,
) -> dict[str, Any]:
    """mode_id=246：七肖七码（正常预测 + 随机平特生肖）。"""
    result = predict(
        config=config,
        res_code=None if is_future else safe_res_code,
        source_table=table_name, db_path=db_path,
        target_hit_rate=default_target_hit_rate,
        random_seed=f"{draw['year']}{draw['term']:03d}" if is_future else None,
    )
    row_data = build_row(
        mode_id=246, lottery_type=str(lottery_type),
        year=str(draw["year"]), term=str(draw["term"]),
        web_value=str(site_web_id), res_code=safe_res_code or "",
        generated_content=result["prediction"]["content"],
    )
    if is_future:
        seed_int = _make_seed_int(f"ping_{draw['year']}{draw['term']:03d}")
        _random.seed(seed_int)
    row_data["ping"] = _random.choice(list({v for v in zodiac_map.values() if v}))
    return row_data


def _generate_mode_331_row(
    draw: dict[str, Any],
    is_future: bool,
    safe_res_code: str | None,
    lottery_type: int,
    site_web_id: int,
    config: Any,
    table_name: str,
    db_path: str | Path,
    default_target_hit_rate: float,
    zodiac_map: dict,
    build_row: Any,
) -> dict[str, Any]:
    """mode_id=331: persist getPmxjcz-compatible x7m14 data into created rows."""
    result = predict(
        config=config,
        res_code=None if is_future else safe_res_code,
        source_table=table_name, db_path=db_path,
        target_hit_rate=default_target_hit_rate,
        random_seed=f"{draw['year']}{draw['term']:03d}" if is_future else None,
    )
    row_data = build_row(
        mode_id=331, lottery_type=str(lottery_type),
        year=str(draw["year"]), term=str(draw["term"]),
        web_value=str(site_web_id), res_code=safe_res_code or "",
        generated_content=result["prediction"]["content"],
    )
    row_data["x7m14"] = _build_mode_331_x7m14(
        result["prediction"].get("labels"),
        zodiac_map,
        f"mode331:{draw['year']}{draw['term']:03d}:{site_web_id}:{lottery_type}",
    )
    return row_data


def _generate_mode_475_row(
    draw: dict[str, Any],
    lottery_type: int,
    site_web_id: int,
    build_row: Any,
    conn: Any,
) -> dict[str, Any]:
    """mode_id=475: build deterministic brain teaser content from static mappings."""
    generated_content = build_brain_teaser_generated_content(
        conn,
        year=int(draw["year"]),
        term=int(draw["term"]),
        site_web_id=int(site_web_id),
    )
    row_data = build_row(
        mode_id=475,
        lottery_type=str(lottery_type),
        year=str(draw["year"]),
        term=str(draw["term"]),
        web_value=str(site_web_id),
        res_code="",
        generated_content=generated_content,
    )
    row_data["source_record_id"] = str(generated_content.get("source_record_id") or "")
    return row_data


def _generate_mode_475_image_url(
    conn: Any,
    *,
    lottery_type: int,
    year: int,
    term: int,
    site_web_id: int,
) -> str:
    current_record = load_brain_teaser_record_for_issue(
        conn,
        year=year,
        term=term,
        site_web_id=site_web_id,
    )
    previous_record = load_previous_brain_teaser_record_for_issue(
        conn,
        year=year,
        term=term,
        site_web_id=site_web_id,
    )
    output_name = MODE_475_OUTPUT_NAME_TEMPLATE.format(
        lottery_type=int(lottery_type),
        year=int(year),
        term=int(term),
        web_id=int(site_web_id),
    )
    output_path = MODE_475_OUTPUT_DIR / output_name
    render_brain_teaser_image(
        current_record=current_record,
        previous_record=previous_record,
        current_issue_text=format_brain_teaser_issue_text(int(term)),
        previous_issue_text=format_brain_teaser_issue_text(max(1, int(term) - 1)),
        output_path=output_path,
    )
    relative_path = output_path.relative_to(_BACKEND_ROOT).as_posix()
    return f"/{relative_path}"


def _generate_mode_474_row(
    draw: dict[str, Any],
    is_future: bool,
    safe_res_code: str | None,
    lottery_type: int,
    site_web_id: int,
    config: Any,
    table_name: str,
    db_path: str | Path,
    default_target_hit_rate: float,
    build_row: Any,
    conn: Any = None,
) -> dict[str, Any]:
    """mode_id=474: use normal prediction content plus a generated image_url."""
    result = predict(
        config=config,
        res_code=None if is_future else safe_res_code,
        source_table=table_name,
        db_path=db_path,
        target_hit_rate=default_target_hit_rate,
        random_seed=f"{draw['year']}{draw['term']:03d}" if is_future else None,
        conn=conn,
    )
    row_data = build_row(
        mode_id=MODE_474_ID,
        lottery_type=str(lottery_type),
        year=str(draw["year"]),
        term=str(draw["term"]),
        web_value=str(site_web_id),
        res_code=safe_res_code or "",
        generated_content=result["prediction"]["content"],
    )
    previous_numbers = _load_previous_opened_numbers_for_issue(
        conn,
        lottery_type_id=int(lottery_type),
        year=int(draw["year"]),
        term=int(draw["term"]),
    )
    if not previous_numbers:
        raise ValueError(
            f"mode_474 缺少对应彩种的上期开奖结果: lottery_type={lottery_type}, "
            f"year={draw['year']}, term={draw['term']}"
        )
    render_result = render_mode_474_prediction_image(
        res_code=previous_numbers,
        lottery_type=int(lottery_type),
        year=int(draw["year"]),
        term=int(draw["term"]),
        site_web_id=int(site_web_id),
    )
    row_data["title"] = render_result.title or build_mode_474_title(draw["term"])
    row_data["image_url"] = render_result.relative_url
    row_data["source_record_id"] = render_result.source_record_id
    return row_data


def _generate_mode_476_row(
    draw: dict[str, Any],
    is_future: bool,
    safe_res_code: str | None,
    lottery_type: int,
    site_web_id: int,
    db_path: str | Path,
    default_target_hit_rate: float,
    build_row: Any,
    conn: Any,
) -> dict[str, Any]:
    """mode_id=476: reuse 跑马图解 7肖14码 text payload and add a generated image_url."""
    try:
        mode_22_config = get_prediction_config("title_22")
    except ValueError:
        mode_22_config = _MODE_476_FALLBACK_CONFIG
    result = predict(
        config=mode_22_config,
        res_code=None if is_future else safe_res_code,
        source_table=mode_22_config.default_table,
        db_path=db_path,
        target_hit_rate=default_target_hit_rate,
        random_seed=f"mode476:{draw['year']}{draw['term']:03d}:{site_web_id}" if is_future else None,
        conn=conn,
    )
    row_data = build_row(
        mode_id=MODE_476_ID,
        lottery_type=str(lottery_type),
        year=str(draw["year"]),
        term=str(draw["term"]),
        web_value=str(site_web_id),
        res_code=safe_res_code or "",
        generated_content=result["prediction"]["content"],
    )
    row_data["title"] = MODE_476_TITLE

    previous_numbers = _load_previous_opened_numbers_for_issue(
        conn,
        lottery_type_id=int(lottery_type),
        year=int(draw["year"]),
        term=int(draw["term"]),
    )
    render_result = render_mode_476_prediction_image(
        lottery_type=int(lottery_type),
        year=int(draw["year"]),
        term=int(draw["term"]),
        site_web_id=int(site_web_id),
        previous_result_numbers=previous_numbers,
    )
    row_data["image_url"] = render_result.relative_url
    row_data["source_record_id"] = render_result.source_record_id
    return row_data


def _generate_mode_478_row(
    draw: dict[str, Any],
    is_future: bool,
    safe_res_code: str | None,
    lottery_type: int,
    site_web_id: int,
    db_path: str | Path,
    default_target_hit_rate: float,
    build_row: Any,
    conn: Any,
) -> dict[str, Any]:
    """mode_id=478: reuse 跑马图解 7肖14码 text payload and add the 台湾跑马图 image_url."""
    try:
        mode_22_config = get_prediction_config("title_22")
    except ValueError:
        mode_22_config = _MODE_478_FALLBACK_CONFIG
    result = predict(
        config=mode_22_config,
        res_code=None if is_future else safe_res_code,
        source_table=mode_22_config.default_table,
        db_path=db_path,
        target_hit_rate=default_target_hit_rate,
        random_seed=f"mode478:{draw['year']}{draw['term']:03d}:{site_web_id}" if is_future else None,
        conn=conn,
    )
    row_data = build_row(
        mode_id=MODE_478_ID,
        lottery_type=str(lottery_type),
        year=str(draw["year"]),
        term=str(draw["term"]),
        web_value=str(site_web_id),
        res_code=safe_res_code or "",
        generated_content=result["prediction"]["content"],
    )
    row_data["title"] = MODE_478_TITLE

    previous_numbers = _load_previous_opened_numbers_for_issue(
        conn,
        lottery_type_id=int(lottery_type),
        year=int(draw["year"]),
        term=int(draw["term"]),
    )
    render_result = render_mode_478_prediction_image(
        lottery_type=int(lottery_type),
        year=int(draw["year"]),
        term=int(draw["term"]),
        site_web_id=int(site_web_id),
        previous_result_numbers=previous_numbers,
    )
    row_data["image_url"] = render_result.relative_url
    row_data["source_record_id"] = render_result.source_record_id
    return row_data


def _generate_default_mode_row(
    draw: dict[str, Any],
    is_future: bool,
    safe_res_code: str | None,
    config: Any,
    table_name: str,
    db_path: str | Path,
    default_target_hit_rate: float,
    build_row: Any,
    lottery_type: int,
    site_web_id: int,
    conn: Any = None,
) -> dict[str, Any]:
    """通用模式：调用 predict() 生成预测内容。"""
    result = predict(
        config=config,
        res_code=None if is_future else safe_res_code,
        source_table=table_name, db_path=db_path,
        target_hit_rate=default_target_hit_rate,
        random_seed=f"{draw['year']}{draw['term']:03d}" if is_future else None,
        conn=conn,
    )
    row_data = build_row(
        mode_id=config.default_modes_id,
        lottery_type=str(lottery_type),
        year=str(draw["year"]), term=str(draw["term"]),
        web_value=str(site_web_id), res_code=safe_res_code or "",
        generated_content=result["prediction"]["content"],
    )
    if int(config.default_modes_id or 0) == 251:
        row_data = _ensure_mode_251_xiao(row_data, result["prediction"]["content"])
    return row_data


def _generate_single_draw_row(
    draw: dict[str, Any],
    mode_id: int,
    is_future: bool,
    safe_res_code: str | None,
    lottery_type: int,
    site_web_id: int,
    config: Any,
    table_name: str,
    db_path: str | Path,
    default_target_hit_rate: float,
    zodiac_map: dict,
    build_row: Any,
    conn: Any = None,
) -> dict[str, Any]:
    """根据 mode_id 分发生成单期预测行。"""
    if mode_id == 65:
        return _generate_mode_65_row(draw, is_future, lottery_type, site_web_id, build_row)
    if mode_id == 108:
        return _generate_mode_108_row(
            draw, is_future, safe_res_code, lottery_type, site_web_id,
            config, table_name, db_path, default_target_hit_rate, build_row,
        )
    if mode_id == 246:
        return _generate_mode_246_row(
            draw, is_future, safe_res_code, lottery_type, site_web_id,
            config, table_name, db_path, default_target_hit_rate, zodiac_map, build_row,
        )
    if mode_id == 331:
        return _generate_mode_331_row(
            draw, is_future, safe_res_code, lottery_type, site_web_id,
            config, table_name, db_path, default_target_hit_rate, zodiac_map, build_row,
        )
    if mode_id == MODE_474_ID:
        return _generate_mode_474_row(
            draw, is_future, safe_res_code, lottery_type, site_web_id,
            config, table_name, db_path, default_target_hit_rate, build_row,
            conn=conn,
        )
    if mode_id == MODE_476_ID:
        return _generate_mode_476_row(
            draw=draw,
            is_future=is_future,
            safe_res_code=safe_res_code,
            lottery_type=lottery_type,
            site_web_id=site_web_id,
            db_path=db_path,
            default_target_hit_rate=default_target_hit_rate,
            build_row=build_row,
            conn=conn,
        )
    if mode_id == MODE_478_ID:
        return _generate_mode_478_row(
            draw=draw,
            is_future=is_future,
            safe_res_code=safe_res_code,
            lottery_type=lottery_type,
            site_web_id=site_web_id,
            db_path=db_path,
            default_target_hit_rate=default_target_hit_rate,
            build_row=build_row,
            conn=conn,
        )
    if mode_id == 475:
        row_data = _generate_mode_475_row(
            draw=draw,
            lottery_type=lottery_type,
            site_web_id=site_web_id,
            build_row=build_row,
            conn=conn,
        )
        row_data["image_url"] = _generate_mode_475_image_url(
            conn,
            lottery_type=int(lottery_type),
            year=int(draw["year"]),
            term=int(draw["term"]),
            site_web_id=int(site_web_id),
        )
        return row_data
    return _generate_default_mode_row(
        draw, is_future, safe_res_code, config, table_name, db_path,
        default_target_hit_rate, build_row, lottery_type, site_web_id,
        conn=conn,
    )


def _persist_generated_row(
    conn: Any,
    table_name: str,
    row_data: dict[str, Any],
    *,
    allow_overwrite: bool,
) -> dict[str, Any]:
    """持久化单行预测结果，自动任务默认只插入缺失行。"""
    if not allow_overwrite:
        existing = find_existing_created_row(conn, table_name, row_data)
        if existing:
            return {
                "action": "skipped_existing",
                "schema": CREATED_SCHEMA_NAME,
                "table": table_name,
                "id": str(existing["id"]),
                "created_at": str(existing["created_at"] or ""),
            }
    return upsert_created_prediction_row(conn, table_name, row_data)


# ── 结构化模块日志 ──────────────────────────────────────


def _write_task_log_to_db(
    db_path: str | Path,
    level: str,
    message: str,
    site_id: int = 0,
    web_id: int = 0,
    lottery_type_id: int = 0,
) -> None:
    """将预测任务日志直接写入 error_logs 表，确保后台日志管理页面可见。"""
    try:
        with connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO error_logs (
                    created_at, level, logger_name, module, func_name,
                    file_path, line_number, message,
                    site_id, web_id, lottery_type_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    level,
                    "prediction.task",
                    "prediction_generation",
                    "_log_module_result",
                    __file__, 0,
                    message,
                    site_id, web_id, lottery_type_id,
                ),
            )
    except Exception:
        pass


def _log_module_result(
    *,
    db_path: str | Path,
    site_id: int,
    site_name: str,
    site_web_id: int,
    lottery_type: int,
    mode_id: int,
    mechanism_key: str,
    report: dict[str, Any],
    elapsed_ms: float,
    trigger: str,
) -> None:
    """输出单个预测模块处理结果的结构化 JSON 日志（文件 + 数据库双写）。"""
    has_error = report.get("errors", 0) > 0
    has_changes = report.get("inserted", 0) > 0 or report.get("updated", 0) > 0

    if has_error:
        status = "error"
    elif has_changes:
        status = "updated"
    else:
        status = "unchanged"

    log_entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "site_id": site_id,
        "site_name": site_name,
        "web_id": site_web_id,
        "lottery_type": lottery_type,
        "mode_id": mode_id,
        "mechanism_key": mechanism_key,
        "table": report.get("table_name", ""),
        "status": status,
        "draw_count": report.get("draw_count", 0),
        "inserted": report.get("inserted", 0),
        "updated": report.get("updated", 0),
        "skipped_existing": report.get("skipped_existing", 0),
        "errors": report.get("errors", 0),
        "elapsed_ms": elapsed_ms,
        "trigger": trigger,
    }

    if report.get("error_message"):
        log_entry["error_message"] = str(report["error_message"])
    if report.get("warnings"):
        log_entry["warnings"] = report["warnings"]

    json_msg = _json.dumps(log_entry, ensure_ascii=False)

    if has_error:
        _task_logger.warning("Module result: %s", json_msg)
        _write_task_log_to_db(db_path, "WARNING", json_msg,
                              site_id=site_id, web_id=site_web_id, lottery_type_id=lottery_type)
    else:
        _task_logger.info("Module result: %s", json_msg)
        if has_changes:
            _write_task_log_to_db(db_path, "INFO", json_msg,
                                  site_id=site_id, web_id=site_web_id, lottery_type_id=lottery_type)


# ── 单模块处理 ───────────────────────────────────────────


def _process_single_module(
    conn: Any,
    module_row: dict[str, Any],
    draws: list[dict[str, Any]],
    future_draws: list[dict[str, Any]],
    future_only: bool,
    safety_draw_map: dict,
    lottery_type: int,
    site_web_id: int,
    db_path: str | Path,
    default_target_hit_rate: float,
    zodiac_map: dict,
    color_map: dict,
    trigger: str,
    allow_overwrite: bool,
    resolve_prediction_table_for_mode: Any,
    build_generated_prediction_row_data: Any,
) -> dict[str, Any]:
    """处理单个模块的所有期号，返回模块报告。"""
    mechanism_key = str(module_row["mechanism_key"] or "")
    mode_id = int(module_row["mode_id"] or 0)

    module_report: dict[str, Any] = {
        "module_id": int(module_row["id"]),
        "mechanism_key": mechanism_key,
        "mode_id": mode_id,
        "table_name": f"mode_payload_{mode_id}" if mode_id > 0 else "",
        "draw_count": len(draws),
        "inserted": 0,
        "updated": 0,
        "skipped_existing": 0,
        "errors": 0,
        "error_message": "",
        "warnings": [],
        "trigger": trigger,
    }

    try:
        config, resolved_mechanism_key, used_fallback_key = _resolve_prediction_config_with_mode_fallback(
            mechanism_key,
            mode_id,
            db_path,
        )
        if used_fallback_key:
            module_report["warnings"].append(
                f"mechanism_key {mechanism_key} is legacy/unknown; fallback to {resolved_mechanism_key} by mode_id={mode_id}"
            )
            mechanism_key = resolved_mechanism_key
            module_report["mechanism_key"] = mechanism_key
        table_name = resolve_prediction_table_for_mode(conn, mode_id, config.default_table)
        module_report["table_name"] = table_name
    except Exception as exc:
        conn.rollback()
        module_report["errors"] += 1
        module_report["error_message"] = str(exc)
        module_report["warnings"].append("module skipped because prediction config/table is unavailable")
        _logger.error(
            "Module generation skipped: mode_id=%d, key=%s — %s",
            mode_id, mechanism_key, exc,
        )
        return module_report

    recent_rows = _load_recent_rows(conn, table_name, lottery_type, site_web_id, mode_id)
    all_target_draws = list(future_draws) if future_only else list(draws) + list(future_draws)

    for draw in all_target_draws:
        try:
            is_future = bool(draw.get("_future"))
            draw_key = (draw["year"], draw["term"])
            safe_res_code = _resolve_safe_res_code(draw, draw_key, safety_draw_map)

            row_data = _generate_single_draw_row(
                draw=draw, mode_id=mode_id, is_future=is_future,
                safe_res_code=safe_res_code, lottery_type=lottery_type,
                site_web_id=site_web_id, config=config, table_name=table_name,
                db_path=db_path, default_target_hit_rate=default_target_hit_rate,
                zodiac_map=zodiac_map, build_row=build_generated_prediction_row_data,
                conn=conn,
            )

            if is_future:
                row_data["res_sx"] = ""
                row_data["res_color"] = ""
            else:
                row_data["res_sx"], row_data["res_color"] = compute_result_fields(
                    draw["numbers_str"], zodiac_map, color_map,
                )

            row_data = enforce_prediction_diversity(
                mode_id=mode_id, row_data=row_data,
                recent_rows=recent_rows, config=config,
            )
            row_data = _repair_text_prediction_diversity(
                conn,
                mode_id=mode_id,
                row_data=row_data,
                recent_rows=recent_rows,
            )
            diversity_warning = row_data.pop("_diversity_warning", None)
            if diversity_warning:
                module_report["warnings"].append(str(diversity_warning))

            stored = _persist_generated_row(
                conn,
                table_name,
                row_data,
                allow_overwrite=allow_overwrite,
            )
            if stored.get("action") == "inserted":
                module_report["inserted"] += 1
                recent_rows.insert(0, {
                    "title": row_data.get("title"),
                    "content": row_data.get("content"),
                    "jiexi": row_data.get("jiexi"),
                })
            elif stored.get("action") == "updated":
                module_report["updated"] += 1
                recent_rows.insert(0, {
                    "title": row_data.get("title"),
                    "content": row_data.get("content"),
                    "jiexi": row_data.get("jiexi"),
                })
            else:
                module_report["skipped_existing"] += 1
        except Exception as exc:
            conn.rollback()
            module_report["errors"] += 1
            if not module_report["error_message"]:
                module_report["error_message"] = str(exc)
            _logger.error(
                "Module generation error: mode_id=%d, key=%s, draw=%s/%d, future=%s — %s",
                mode_id, mechanism_key, draw.get("year"), draw.get("term"),
                draw.get("_future", False), exc,
            )

    return module_report


# ── 主入口 ──────────────────────────────────────────────


def generate_prediction_batch(
    db_path: str | Path,
    *,
    site_id: int,
    lottery_type: int,
    start_issue: tuple[int, int],
    end_issue: tuple[int, int],
    mechanism_keys: list[str] | None,
    future_periods: int,
    future_only: bool,
    trigger: str,
    allow_overwrite: bool = True,
    sync_site_modules: Any,
    resolve_prediction_table_for_mode: Any,
    build_generated_prediction_row_data: Any,
) -> dict[str, Any]:
    """批量生成预测资料的编排入口。

    params:
    - db_path: 数据库目标。
    - site_id: 站点 ID。
    - lottery_type: 彩种类型 ID。
    - start_issue / end_issue: 期号范围 (year, term)。
    - mechanism_keys: 要生成的机制键列表（None 表示全部）。
    - future_periods: 未来期号数量。
    - future_only: 是否只生成未来期。
    - trigger: 触发来源标识。
    - allow_overwrite: 是否允许覆盖既有 created 预测正文。
    - sync_site_modules / resolve_prediction_table_for_mode /
      build_generated_prediction_row_data: 回调函数。

    returns:
        生成结果摘要字典。
    """
    _t_start = time.perf_counter()
    requested_keys = list(mechanism_keys or [])

    _logger.info(
        "Batch generation started: site_id=%d, keys=%s, range=%s-%s, future=%d, future_only=%s, trigger=%s",
        site_id, requested_keys or ["all"],
        f"{start_issue[0]}{start_issue[1]:03d}",
        f"{end_issue[0]}{end_issue[1]:03d}",
        future_periods, bool(future_only), trigger,
    )

    ensure_prediction_configs_loaded(db_path)
    site_web_id, site_name = _resolve_generation_context(db_path, site_id)

    with connect(db_path) as conn:
        sync_site_modules(conn, site_id)
        zodiac_map, color_map = load_fixed_data_maps(conn)
        default_target_hit_rate = _default_target_hit_rate(conn)
        max_terms_per_year = _max_terms_per_year(conn)

        module_rows = conn.execute(
            """
            SELECT id, mechanism_key, mode_id, status, sort_order
            FROM site_prediction_modules
            WHERE site_id = ? AND status = 1
            """
            + (
                f" AND mechanism_key IN ({', '.join('?' for _ in requested_keys)})"
                if requested_keys else ""
            )
            + " ORDER BY sort_order, id",
            [site_id] + (requested_keys if requested_keys else []),
        ).fetchall()

        draws = list_opened_draws_in_issue_range(conn, lottery_type, start_issue, end_issue)
        if not draws and future_only and int(future_periods or 0) > 0:
            fallback_draw = find_latest_opened_draw_before_issue(conn, lottery_type, start_issue)
            if fallback_draw:
                draws = [fallback_draw]
        # 纯未来期生成时，若无任何已开奖记录，用 start_issue 的前一期作为推算基准
        if not draws and future_only and int(future_periods or 0) > 0:
            ref_year, ref_term = start_issue
            if ref_term > 1:
                ref_term -= 1
            else:
                ref_year -= 1
                ref_term = max_terms_per_year
            draws = [{"year": ref_year, "term": ref_term, "numbers_str": ""}]
        if not draws:
            raise ValueError("指定期号范围内没有可用的已开奖数据。")

        future_draws = _build_future_draws(
            draws, future_periods, start_issue, end_issue,
            future_only, max_terms_per_year,
        )
        safety_draw_map = _build_safety_draw_map(conn, lottery_type)

        module_reports: list[dict[str, Any]] = []
        total_inserted = 0
        total_updated = 0
        total_skipped_existing = 0
        total_errors = 0

        for module_row in module_rows:
            mechanism_key = str(module_row["mechanism_key"] or "")
            mode_id = int(module_row["mode_id"] or 0)
            module_t0 = time.perf_counter()

            report = _process_single_module(
                conn=conn, module_row=module_row, draws=draws,
                future_draws=future_draws, future_only=future_only,
                safety_draw_map=safety_draw_map, lottery_type=int(lottery_type),
                site_web_id=site_web_id, db_path=db_path,
                default_target_hit_rate=default_target_hit_rate,
                zodiac_map=zodiac_map, color_map=color_map,
                trigger=trigger, allow_overwrite=bool(allow_overwrite),
                resolve_prediction_table_for_mode=resolve_prediction_table_for_mode,
                build_generated_prediction_row_data=build_generated_prediction_row_data,
            )
            module_reports.append(report)
            total_inserted += report["inserted"]
            total_updated += report["updated"]
            total_skipped_existing += report["skipped_existing"]
            total_errors += report["errors"]

            # 结构化日志：每个模块的处理结果
            _log_module_result(
                db_path=db_path,
                site_id=int(site_id), site_name=site_name,
                site_web_id=site_web_id, lottery_type=int(lottery_type),
                mode_id=mode_id, mechanism_key=mechanism_key,
                report=report, elapsed_ms=round((time.perf_counter() - module_t0) * 1000, 1),
                trigger=trigger,
            )

        elapsed_s = round(time.perf_counter() - _t_start, 2)
        _logger.info(
            "Batch generation completed: modules=%d, draws=%d, inserted=%d, updated=%d, skipped_existing=%d, errors=%d, elapsed=%.1fs",
            len(module_reports), len(draws), total_inserted, total_updated,
            total_skipped_existing, total_errors, elapsed_s,
        )
        if total_errors > 0:
            _logger.warning(
                "Batch generation had %d errors across %d modules",
                total_errors,
                sum(1 for m in module_reports if m.get("errors", 0) > 0),
            )

        # 站点级汇总日志
        _task_logger.info(
            "Site summary: %s",
            _json.dumps({
                "ts": datetime.now(timezone.utc).isoformat(),
                "site_id": int(site_id),
                "site_name": site_name,
                "web_id": site_web_id,
                "lottery_type": int(lottery_type),
                "start_issue": f"{start_issue[0]}{start_issue[1]:03d}",
                "end_issue": f"{end_issue[0]}{end_issue[1]:03d}",
                "total_modules": len(module_reports),
                "draw_count": len(draws),
                "future_periods": int(future_periods or 0),
                "future_only": bool(future_only),
                "inserted": total_inserted,
                "updated": total_updated,
                "skipped_existing": total_skipped_existing,
                "errors": total_errors,
                "elapsed_s": elapsed_s,
                "trigger": trigger,
                "allow_overwrite": bool(allow_overwrite),
            }, ensure_ascii=False),
        )

        return {
            "site_id": int(site_id),
            "site_name": site_name,
            "lottery_type": int(lottery_type),
            "start_issue": f"{start_issue[0]}{start_issue[1]}",
            "end_issue": f"{end_issue[0]}{end_issue[1]}",
            "web_id": site_web_id,
            "future_periods": int(future_periods or 0),
            "future_only": bool(future_only),
            "total_modules": len(module_reports),
            "draw_count": len(draws),
            "inserted": total_inserted,
            "updated": total_updated,
            "skipped_existing": total_skipped_existing,
            "errors": total_errors,
            "trigger": trigger,
            "allow_overwrite": bool(allow_overwrite),
            "modules": module_reports,
        }
