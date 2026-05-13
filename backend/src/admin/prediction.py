"""
Admin 预测管理 —— 模块同步 / 生成 / 批量操作 / 安全控制。

提供以下核心能力：
- 站点预测模块的同步与蓝图查询
- 预测行数据的构建与规范化
- 开奖可见性安全控制（防止未开奖期次泄露号码）
- 预测 API 响应构建
- 期号范围解析与已开奖数据查询
- 批量生成预测数据 & 单表重生成

从 app.py 提取，不改变任何函数签名与行为。
"""
from __future__ import annotations

import json
from typing import Any

from db import utc_now

# 从 domains 层导入已迁移的核心生成函数（消除反向依赖）
from domains.prediction.generation_service import (  # noqa: F401 - 兼容导出
    build_generated_prediction_row_data,
    get_site_prediction_module_blueprint_by_key,
    get_site_prediction_module_blueprints,
    parse_issue_range_value,
    resolve_prediction_table_for_mode,
    sync_site_prediction_modules,
)
# 从 domains 层导入安全控制函数（消除反向依赖）
from domains.prediction.safety_service import (  # noqa: F401 - 兼容导出
    apply_prediction_row_safety,
    lookup_draw_visibility,
    redact_prediction_result_fields,
    resolve_prediction_request_safety,
)
# 从 domains 层导入重新生成函数（消除反向依赖）
from domains.prediction.regeneration_service import (  # noqa: F401 - 兼容导出
    compute_res_fields,
    regenerate_payload_data,
)







def normalize_prediction_display_text(content: Any) -> str:
    """将预测内容统一转为前端可直接展示的文本字符串。

    :param content: 预测内容（可为 None、str、dict、list 等任意类型）
    :return: 标准化后的展示文本字符串
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, (dict, list)):
        return json.dumps(content, ensure_ascii=False)
    return str(content)




# ─────────────────────────────────────────────────────────
# API 响应构建 / API response construction
# ─────────────────────────────────────────────────────────

def build_prediction_api_response(
    *,
    mechanism_key: str,
    request_payload: dict[str, Any],
    raw_result: dict[str, Any],
    safety: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """将 ``predict()`` 的原始返回包装成对外稳定的 HTTP 协议格式。

    构建一个标准化的 API 响应字典，包含以下区块：
    - mechanism: 预测机制元信息
    - source: 数据源信息
    - request: 回显的请求参数
    - context: 上下文信息（最新期次、开奖可见性）
    - prediction: 预测结果（含标签、文本）
    - backtest: 回测结果
    - explanation: 解释信息
    - warning: 警告信息

    :param mechanism_key: 预测机制的唯一标识 key
    :param request_payload: 前端请求参数字典
    :param raw_result: ``predict()`` 的原始返回结果
    :param safety: 可选，开奖可见性字典（由 ``lookup_draw_visibility`` 返回）
    :return: 标准化的 API 响应字典
    """
    prediction_block = raw_result.get("prediction") or {}
    normalized_safety = dict(safety or {})

    if "result_visibility" not in normalized_safety:
        normalized_safety["result_visibility"] = "unknown"
    if "reason" not in normalized_safety:
        normalized_safety["reason"] = "not_evaluated"

    return {
        "ok": True,
        "protocol_version": 1,
        "generated_at": utc_now(),
        "data": {
            "mechanism": {
                "key": str(raw_result.get("mode", {}).get("key") or mechanism_key),
                "title": str(raw_result.get("mode", {}).get("title") or ""),
                "default_modes_id": raw_result.get("mode", {}).get("default_modes_id"),
                "default_table": str(raw_result.get("mode", {}).get("default_table") or ""),
                "resolved_labels": list(raw_result.get("mode", {}).get("resolved_labels") or []),
            },
            "source": {
                "db_path": str(raw_result.get("source", {}).get("db_path") or ""),
                "table": str(raw_result.get("source", {}).get("table") or ""),
                "source_modes_id": raw_result.get("source", {}).get("source_modes_id"),
                "source_table_title": str(raw_result.get("source", {}).get("source_table_title") or ""),
                "history_count": raw_result.get("source", {}).get("history_count"),
            },
            "request": {
                "res_code": request_payload.get("res_code"),
                "content": request_payload.get("content"),
                "source_table": request_payload.get("source_table"),
                "target_hit_rate": request_payload.get("target_hit_rate"),
                "lottery_type": request_payload.get("lottery_type"),
                "year": request_payload.get("year"),
                "term": request_payload.get("term"),
                "web": request_payload.get("web"),
            },
            "context": {
                "latest_term": raw_result.get("input", {}).get("latest_term"),
                "latest_outcome": raw_result.get("input", {}).get("latest_outcome"),
                "draw": normalized_safety,
            },
            "prediction": {
                "labels": list(prediction_block.get("labels") or []),
                "content": prediction_block.get("content"),
                "content_json": str(prediction_block.get("content_json") or ""),
                "display_text": normalize_prediction_display_text(prediction_block.get("content")),
            },
            "backtest": dict(raw_result.get("backtest") or {}),
            "explanation": list(raw_result.get("explanation") or []),
            "warning": str(raw_result.get("warning") or ""),
        },
        "legacy": raw_result,
    }


# ─────────────────────────────────────────────────────────
# 期号范围解析 & 开奖数据查询
# Issue range parsing & draw data query
# ─────────────────────────────────────────────────────────

def list_opened_draws_in_issue_range(
    conn: Any,
    lottery_type_id: int,
    start_issue: tuple[int, int],
    end_issue: tuple[int, int],
) -> list[dict[str, Any]]:
    """获取指定彩种、指定期号范围内的已开奖期次列表。

    返回仅包含已开奖（is_opened=1）且在期号范围内的记录，
    号码会规范化为两位数格式（如 "01,15,23,..."）。

    :param conn: 数据库连接对象
    :param lottery_type_id: 彩种类型 ID
    :param start_issue: 起始期号 (year, term) 元组
    :param end_issue: 结束期号 (year, term) 元组
    :return: 已开奖期次列表，每个元素包含 year、term、numbers_str 字段
    """
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

        if current < start_issue:
            continue
        if current > end_issue:
            continue

        raw_numbers = str(row["numbers"] or "")
        normalized_numbers: list[str] = []
        for n in raw_numbers.split(","):
            n = n.strip()
            if not n:
                continue
            try:
                normalized_numbers.append(f"{int(n):02d}")
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


# 向后兼容别名（被 crawler_service.py 引用）
_compute_res_fields = compute_res_fields

# 向后兼容函数（委托给 domains.prediction.service）
def bulk_generate_site_prediction_data(
    db_path: str | Path,
    site_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """为站点批量生成预测数据（兼容入口，请使用 domains.prediction.service.bulk_generate_site_predictions）。"""
    from domains.prediction.service import bulk_generate_site_predictions
    return bulk_generate_site_predictions(db_path, site_id, payload)
