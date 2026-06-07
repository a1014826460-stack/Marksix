from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from db import connect
from helpers import load_fixed_data_maps, split_csv
from legacy.api import load_legacy_mode_rows
from public.api import resolve_public_site


SUPPORTED_MODULE_KEYS = (
    "wuxiao_wuma",
    "public_yixiao_yima",
    "shuangbo_12ma",
    "shujinguang",
    "daxiao_2tou",
    "tiandi_2xiao",
)


@dataclass(frozen=True)
class VendorModuleContext:
    site: dict[str, Any]
    lottery_type: int
    web_id: int
    history_limit: int


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        return default


def _parse_json_array(value: Any) -> list[Any]:
    raw = str(value or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except Exception:
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1]
            quoted_items = re.findall(r'"([^"]+)"', inner)
            if quoted_items:
                return quoted_items
        return []
    return parsed if isinstance(parsed, list) else []


def _split_labels(value: Any) -> list[str]:
    items = [item.strip() for item in split_csv(value) if str(item).strip()]
    if items and not (len(items) == 1 and re.fullmatch(r"[鼠牛虎兔龙蛇马羊猴鸡狗猪]+", items[0])):
        return items

    text = str(value or "").strip()
    if not text:
        return []
    if "|" in text:
        text = text.split("|", 1)[0].strip()
    zodiacs = re.findall(r"[鼠牛虎兔龙蛇马羊猴鸡狗猪]", text)
    return zodiacs if zodiacs else ([text] if text else [])


def _split_codes_from_text(value: Any) -> list[str]:
    text = str(value or "")
    for token in ("|", ":", "："):
        if token in text:
            text = text.split(token, 1)[1]
            break
    normalized = text.replace("，", ",").replace(".", ",").replace("。", ",")
    values: list[str] = []
    for item in normalized.split(","):
        item_text = item.strip()
        if not item_text:
            continue
        try:
            values.append(f"{int(item_text):02d}")
        except ValueError:
            continue
    return values


def _parse_label_code_pairs(value: Any) -> list[tuple[str, list[str]]]:
    items = _parse_json_array(value)
    pairs: list[tuple[str, list[str]]] = []
    for item in items:
        text = str(item or "").strip()
        if not text:
            continue
        if "|" in text:
            label, codes_raw = text.split("|", 1)
            codes = _split_codes_from_text(codes_raw)
            pairs.append((label.strip(), codes))
            continue
        pieces = _split_labels(text)
        if pieces:
            pairs.append((pieces[0], []))
    if pairs:
        return pairs

    text = str(value or "").strip()
    if not text:
        return []

    pair_matches = re.findall(r"([鼠牛虎兔龙蛇马羊猴鸡狗猪])\|([0-9,\s]+)", text)
    if pair_matches:
        return [
            (label, _split_codes_from_text(codes_raw))
            for label, codes_raw in pair_matches
        ]

    return [(label, []) for label in _split_labels(text)]
    


def _pick_result(row: dict[str, Any]) -> dict[str, Any]:
    codes = _split_labels(row.get("res_code"))
    zodiacs = _split_labels(row.get("res_sx"))
    colors = _split_labels(row.get("res_color"))
    special_code = codes[-1] if codes else ""
    special_sx = zodiacs[-1] if zodiacs else ""
    special_color = colors[-1] if colors else ""
    is_opened = bool(row.get("draw_is_opened")) and bool(special_code)
    result_text = "待开奖"
    if is_opened:
        result_text = f"开{special_code}{special_sx}".strip()
    return {
        "res_code": special_code,
        "res_sx": special_sx,
        "res_color": special_color,
        "result_text": result_text,
        "is_opened": bool(row.get("draw_is_opened")),
    }


def _hit_text(row: dict[str, Any]) -> str:
    result = _pick_result(row)
    if not result["is_opened"]:
        return "???????"
    suffix = "对" if result["res_code"] else "错"
    if result["res_code"] and result["res_sx"]:
        suffix = "对"
    return f"{result['res_code']}{result['res_sx']}{suffix}".strip()


def _normalize_issue(row: dict[str, Any]) -> str:
    return f"{row.get('year') or ''}{row.get('term') or ''}".strip()


def _load_mode_rows(
    db_path: str | Any,
    *,
    modes_id: int,
    web_id: int,
    lottery_type: int,
    limit: int,
) -> list[dict[str, Any]]:
    payload = load_legacy_mode_rows(
        db_path,
        modes_id=modes_id,
        limit=limit,
        web=web_id,
        type_value=lottery_type,
    )
    return [dict(row) for row in payload.get("rows") or []]


def _rows_by_issue(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {_normalize_issue(row): row for row in rows if _normalize_issue(row)}


def _history_window(*row_groups: list[dict[str, Any]], limit: int) -> list[str]:
    merged: dict[str, tuple[int, str]] = {}
    for rows in row_groups:
        for row in rows:
            issue = _normalize_issue(row)
            if not issue:
                continue
            sort_key = (_safe_int(row.get("year")), f"{_safe_int(row.get('term')):03d}")
            merged[issue] = sort_key
    ordered = sorted(merged.items(), key=lambda item: item[1], reverse=True)
    return [issue for issue, _ in ordered[:limit]]


def _build_wuxiao_wuma(ctx: VendorModuleContext, db_path: str | Any) -> dict[str, Any]:
    x4_rows = _load_mode_rows(db_path, modes_id=47, web_id=ctx.web_id, lottery_type=ctx.lottery_type, limit=ctx.history_limit)
    x3_rows = _load_mode_rows(db_path, modes_id=69, web_id=ctx.web_id, lottery_type=ctx.lottery_type, limit=ctx.history_limit)
    yx_rows = _load_mode_rows(db_path, modes_id=151, web_id=ctx.web_id, lottery_type=ctx.lottery_type, limit=ctx.history_limit)
    by4 = _rows_by_issue(x4_rows)
    by3 = _rows_by_issue(x3_rows)
    byy = _rows_by_issue(yx_rows)
    history: list[dict[str, Any]] = []
    for issue in _history_window(yx_rows, x4_rows, x3_rows, limit=ctx.history_limit):
        rowy = byy.get(issue)
        if not rowy:
            continue
        row4 = by4.get(issue)
        row3 = by3.get(issue)
        pairs = _parse_label_code_pairs(rowy.get("content"))
        x5 = [label for label, _ in pairs][:5]
        x4 = _split_labels(row4.get("content"))[:4] if row4 else x5[:4]
        x3 = _split_labels(row3.get("content"))[:3] if row3 else x5[:3]
        code_map = {label: codes for label, codes in pairs}
        ordered_codes: list[str] = []
        for label in x5:
            for code in code_map.get(label, []):
                if code not in ordered_codes:
                    ordered_codes.append(code)
        groups = {
            "xiao_5": x5,
            "xiao_4": x4,
            "xiao_3": x3,
            "xiao_2": x5[:2],
            "code_5": ordered_codes[:5],
            "code_4": ordered_codes[:4],
            "code_3": ordered_codes[:3],
            "code_2": ordered_codes[:2],
        }
        result = _pick_result(rowy)
        history.append(
            {
                "issue": issue,
                "year": str(rowy.get("year") or ""),
                "term": str(rowy.get("term") or ""),
                "groups": groups,
                "result": result,
                "is_opened": result["is_opened"],
                "is_correct": None,
                "raw": {"source_mode_ids": [47, 69, 151]},
            }
        )
    return {
        "module_key": "wuxiao_wuma",
        "title": "五肖五码",
        "display_style": "table-composite",
        "history": history,
    }


def _build_public_yixiao_yima(ctx: VendorModuleContext, db_path: str | Any) -> dict[str, Any]:
    x9_rows = _load_mode_rows(db_path, modes_id=49, web_id=ctx.web_id, lottery_type=ctx.lottery_type, limit=ctx.history_limit)
    x1_rows = _load_mode_rows(db_path, modes_id=151, web_id=ctx.web_id, lottery_type=ctx.lottery_type, limit=ctx.history_limit)
    by9 = _rows_by_issue(x9_rows)
    by1 = _rows_by_issue(x1_rows)
    history: list[dict[str, Any]] = []
    for issue in _history_window(x9_rows, x1_rows, limit=ctx.history_limit):
        row9 = by9.get(issue)
        row1 = by1.get(issue)
        if not row9 or not row1:
            continue
        x9 = _split_labels(row9.get("content"))[:9]
        pairs1 = _parse_label_code_pairs(row1.get("content"))
        x7 = x9[:7]
        x5 = x9[:5]
        x3 = x9[:3]
        code14: list[str] = []
        for _label, codes in pairs1:
            for code in codes:
                if code not in code14:
                    code14.append(code)
        best_xiao = ""
        best_code = ""
        if pairs1:
            best_xiao = pairs1[0][0]
            best_code = pairs1[0][1][0] if pairs1[0][1] else ""
        result = _pick_result(row1)
        is_correct = None
        if result["is_opened"] and best_xiao and best_code:
            is_correct = result["res_sx"] == best_xiao or result["res_code"] == best_code
        history.append(
            {
                "issue": issue,
                "year": str(row1.get("year") or ""),
                "term": str(row1.get("term") or ""),
                "xiao_groups": {
                    "xiao_9": x9,
                    "xiao_7": x7,
                    "xiao_5": x5,
                    "xiao_3": x3,
                },
                "code_groups": {
                    "code_14": code14[:14],
                    "code_8": code14[:8],
                    "code_5": code14[:5],
                },
                "best_pick": {
                    "xiao": best_xiao,
                    "code": best_code,
                    "text": f"本期推荐一肖一码:({best_xiao}{best_code})" if (best_xiao or best_code) else "",
                },
                "result": result,
                "is_opened": result["is_opened"],
                "is_correct": is_correct,
                "raw": {"source_mode_ids": [49, 44, 151]},
            }
        )
    return {
        "module_key": "public_yixiao_yima",
        "title": "公开一肖一码",
        "display_style": "card-composite",
        "history": history,
    }


def _codes_for_wave_labels(
    color_number_map: dict[str, list[str]],
    labels: list[str],
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for label in labels:
        codes = color_number_map.get(label, [])
        if not codes:
            continue
        groups.append({"label": label, "codes": codes[:12]})
    return groups


def _build_shuangbo_12ma(ctx: VendorModuleContext, db_path: str | Any) -> dict[str, Any]:
    sb_rows = _load_mode_rows(db_path, modes_id=38, web_id=ctx.web_id, lottery_type=ctx.lottery_type, limit=ctx.history_limit)
    history: list[dict[str, Any]] = []
    with connect(db_path) as conn:
        _zodiac_map, color_map = load_fixed_data_maps(conn)
    color_number_map: dict[str, list[str]] = {}
    for code_text, label in color_map.items():
        if not code_text.isdigit() or len(code_text) != 2:
            continue
        color_number_map.setdefault(label, [])
        if code_text not in color_number_map[label]:
            color_number_map[label].append(code_text)
    for row in sb_rows[: ctx.history_limit]:
        labels = _split_labels(row.get("content"))[:2]
        result = _pick_result(row)
        history.append(
            {
                "issue": _normalize_issue(row),
                "year": str(row.get("year") or ""),
                "term": str(row.get("term") or ""),
                "wave_groups": _codes_for_wave_labels(color_number_map, labels),
                "result": result,
                "is_opened": result["is_opened"],
                "is_correct": None,
                "raw": {"source_mode_ids": [38]},
            }
        )
    return {
        "module_key": "shuangbo_12ma",
        "title": "双波12码",
        "display_style": "wave-composite",
        "history": history,
    }


def _build_shujinguang(ctx: VendorModuleContext, db_path: str | Any) -> dict[str, Any]:
    x7_rows = _load_mode_rows(db_path, modes_id=44, web_id=ctx.web_id, lottery_type=ctx.lottery_type, limit=ctx.history_limit)
    history: list[dict[str, Any]] = []
    for row in x7_rows[: ctx.history_limit]:
        pairs = _parse_label_code_pairs(row.get("content"))
        if len(pairs) < 2:
            continue
        picks = [pairs[0][0], pairs[1][0]]
        result = _pick_result(row)
        is_correct = None
        if result["is_opened"] and result["res_sx"]:
            is_correct = result["res_sx"] not in picks
        history.append(
            {
                "issue": _normalize_issue(row),
                "year": str(row.get("year") or ""),
                "term": str(row.get("term") or ""),
                "picks": picks,
                "text": f"{str(row.get('term') or '')}期本期【{'.'.join(picks)}】输尽光",
                "result": result,
                "result_text": _hit_text(row),
                "is_opened": result["is_opened"],
                "is_correct": is_correct,
                "raw": {"source_mode_ids": [44], "derived_from": "七肖7码前二肖"},
            }
        )
    return {
        "module_key": "shujinguang",
        "title": "输尽光",
        "display_style": "single-line",
        "history": history,
    }


def _extract_daxiao_label(row: dict[str, Any]) -> str:
    pairs = _parse_label_code_pairs(row.get("content"))
    if pairs:
        return pairs[0][0]
    labels = _split_labels(row.get("content"))
    return labels[0] if labels else ""


def _extract_tou_label(row: dict[str, Any]) -> str:
    direct_pairs = _parse_label_code_pairs(row.get("content"))
    if direct_pairs and direct_pairs[0][1]:
        return direct_pairs[0][1][0]
    values = _parse_json_array(row.get("tou"))
    if values:
        return str(values[0] or "").replace("头", "").strip()
    labels = _split_labels(row.get("content"))
    if labels:
        digits = "".join(ch for ch in labels[0] if ch.isdigit())
        return digits
    return ""


def _build_daxiao_2tou(ctx: VendorModuleContext, db_path: str | Any) -> dict[str, Any]:
    dx_rows = _load_mode_rows(db_path, modes_id=57, web_id=ctx.web_id, lottery_type=ctx.lottery_type, limit=ctx.history_limit)
    tou_rows = _load_mode_rows(db_path, modes_id=108, web_id=ctx.web_id, lottery_type=ctx.lottery_type, limit=ctx.history_limit)
    bydx = _rows_by_issue(dx_rows)
    bytou = _rows_by_issue(tou_rows)
    history: list[dict[str, Any]] = []
    for issue in _history_window(dx_rows, tou_rows, limit=ctx.history_limit):
        dx_row = bydx.get(issue)
        tou_row = bytou.get(issue)
        if not dx_row or not tou_row:
            continue
        dx_label = _extract_daxiao_label(dx_row)
        tou_label = _extract_tou_label(tou_row)
        result = _pick_result(tou_row)
        is_correct = None
        if result["is_opened"] and result["res_code"]:
            try:
                code_int = int(result["res_code"])
                dx_ok = (dx_label == "大" and code_int >= 25) or (dx_label == "小" and code_int <= 24)
                tou_ok = str(code_int).zfill(2).startswith(tou_label)
                is_correct = dx_ok or tou_ok
            except ValueError:
                is_correct = None
        history.append(
            {
                "issue": issue,
                "year": str(tou_row.get("year") or ""),
                "term": str(tou_row.get("term") or ""),
                "daxiao": dx_label,
                "tou_code": tou_label,
                "display_text": f"【{dx_label}数+{tou_label}】",
                "result": result,
                "is_opened": result["is_opened"],
                "is_correct": is_correct,
                "raw": {"source_mode_ids": [57, 108]},
            }
        )
    return {
        "module_key": "daxiao_2tou",
        "title": "大小+2头",
        "display_style": "single-line",
        "history": history,
    }


def _extract_tiandi_label(row: dict[str, Any]) -> str:
    pairs = _parse_label_code_pairs(row.get("content"))
    if pairs:
        return pairs[0][0]
    labels = _split_labels(row.get("content"))
    return labels[0] if labels else ""


def _extract_two_xiao(row: dict[str, Any]) -> list[str]:
    title = str(row.get("title") or "")
    if "|" in title:
        _prefix, labels = title.split("|", 1)
        items = _split_labels(labels)
        if items:
            return items[:2]
    labels = _split_labels(row.get("xiao"))
    return labels[:2]


def _build_tiandi_2xiao(ctx: VendorModuleContext, db_path: str | Any) -> dict[str, Any]:
    td_rows = _load_mode_rows(db_path, modes_id=5, web_id=ctx.web_id, lottery_type=ctx.lottery_type, limit=ctx.history_limit)
    x2_rows = _load_mode_rows(db_path, modes_id=251, web_id=ctx.web_id, lottery_type=ctx.lottery_type, limit=ctx.history_limit)
    bytd = _rows_by_issue(td_rows)
    byx2 = _rows_by_issue(x2_rows)
    history: list[dict[str, Any]] = []
    for issue in _history_window(td_rows, x2_rows, limit=ctx.history_limit):
        td_row = bytd.get(issue)
        x2_row = byx2.get(issue)
        if not td_row or not x2_row:
            continue
        result = _pick_result(td_row)
        labels = _extract_two_xiao(x2_row)
        tiandi = _extract_tiandi_label(td_row)
        is_correct = None
        if result["is_opened"] and result["res_sx"]:
            is_correct = result["res_sx"] in labels
        history.append(
            {
                "issue": issue,
                "year": str(td_row.get("year") or ""),
                "term": str(td_row.get("term") or ""),
                "tiandi": tiandi,
                "xiao_pair": labels,
                "display_text": f"【{tiandi}+{''.join(labels)}】",
                "result": result,
                "is_opened": result["is_opened"],
                "is_correct": is_correct,
                "raw": {"source_mode_ids": [5, 251]},
            }
        )
    return {
        "module_key": "tiandi_2xiao",
        "title": "天地两肖",
        "display_style": "single-line",
        "history": history,
    }


def build_vendor_homepage_modules(
    db_path: str | Any,
    *,
    site_id: int,
    lottery_type: int | None = None,
    module_keys: list[str] | None = None,
    history_limit: int = 8,
) -> dict[str, Any]:
    site = resolve_public_site(db_path, site_id=site_id)
    resolved_lottery_type = _safe_int(lottery_type, _safe_int(site.get("lottery_type_id"), 1))
    ctx = VendorModuleContext(
        site=site,
        lottery_type=resolved_lottery_type,
        web_id=_safe_int(site.get("web_id")),
        history_limit=max(1, min(_safe_int(history_limit, 8), 20)),
    )
    requested_keys = [key for key in (module_keys or list(SUPPORTED_MODULE_KEYS)) if key in SUPPORTED_MODULE_KEYS]
    builders = {
        "wuxiao_wuma": _build_wuxiao_wuma,
        "public_yixiao_yima": _build_public_yixiao_yima,
        "shuangbo_12ma": _build_shuangbo_12ma,
        "shujinguang": _build_shujinguang,
        "daxiao_2tou": _build_daxiao_2tou,
        "tiandi_2xiao": _build_tiandi_2xiao,
    }
    data = [builders[key](ctx, db_path) for key in requested_keys]
    return {
        "ok": True,
        "site": {
            "site_id": _safe_int(site.get("id")),
            "web_id": _safe_int(site.get("web_id")),
            "site_key": "twcaibawang" if _safe_int(site.get("web_id")) == 5 else "vendor",
            "lottery_type": resolved_lottery_type,
        },
        "data": data,
    }
