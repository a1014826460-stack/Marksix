from __future__ import annotations

import json
from typing import Any

from db import utc_now


def normalize_prediction_display_text(content: Any) -> str:
    """Normalize prediction content into frontend-displayable text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, (dict, list)):
        return json.dumps(content, ensure_ascii=False)
    return str(content)


def build_prediction_api_response(
    *,
    mechanism_key: str,
    request_payload: dict[str, Any],
    raw_result: dict[str, Any],
    safety: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Wrap raw prediction results in the stable public HTTP API shape."""
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
