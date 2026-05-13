"""预测安全控制服务。

提供开奖可见性查询、结果字段抹除、预测请求安全检查等核心业务逻辑。
供 routes 层和 prediction_generation 层复用。
"""

from __future__ import annotations

from typing import Any

from helpers import parse_issue_int


def lookup_draw_visibility(
    conn: Any,
    *,
    lottery_type: Any = "",
    year: Any = "",
    term: Any = "",
) -> dict[str, Any]:
    """查询指定期次的开奖可见性。

    根据 lottery_draws 表中的 is_opened 字段判断该期是否已开奖：
    - 已开奖（is_opened=1）：result_visibility = "visible"
    - 未开奖（is_opened=0）：result_visibility = "hidden"
    - 找不到记录：result_visibility = "unknown"
    """
    lottery_type_id = parse_issue_int(lottery_type)
    year_value = parse_issue_int(year)
    term_value = parse_issue_int(term)

    issue = f"{year_value or ''}{term_value or ''}".strip()
    context: dict[str, Any] = {
        "issue": issue or "",
        "lottery_type": str(lottery_type or ""),
        "year": str(year or ""),
        "term": str(term or ""),
        "lottery_type_id": lottery_type_id,
        "year_value": year_value,
        "term_value": term_value,
    }

    if lottery_type_id is None or year_value is None or term_value is None:
        context["result_visibility"] = "unknown"
        context["reason"] = "missing_issue_context"
        return context

    row = conn.execute(
        """
        SELECT is_opened
        FROM lottery_draws
        WHERE lottery_type_id = ?
          AND year = ?
          AND term = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (lottery_type_id, year_value, term_value),
    ).fetchone()

    if not row:
        context["result_visibility"] = "unknown"
        context["reason"] = "draw_not_found"
        return context

    is_opened = bool(row["is_opened"])
    context["is_opened"] = is_opened
    context["reason"] = "draw_found"
    context["result_visibility"] = "visible" if is_opened else "hidden"
    return context


def redact_prediction_result_fields(row_data: dict[str, Any]) -> dict[str, Any]:
    """统一抹除开奖结果字段，避免未开奖期次泄露号码、生肖、波色。

    将 res_code、res_sx、res_color 三个字段置为空字符串。
    """
    sanitized = dict(row_data)
    for field_name in ("res_code", "res_sx", "res_color"):
        sanitized[field_name] = ""
    return sanitized


def apply_prediction_row_safety(
    conn: Any,
    row_data: dict[str, Any],
    *,
    lottery_type: Any = "",
    year: Any = "",
    term: Any = "",
) -> dict[str, Any]:
    """根据开奖状态决定是否需要对预测行数据做安全处理。

    如果目标期次尚未开奖，则抹除 res_code / res_sx / res_color 字段；
    否则原样返回。
    """
    visibility = lookup_draw_visibility(
        conn,
        lottery_type=lottery_type,
        year=year,
        term=term,
    )
    if visibility.get("result_visibility") == "hidden":
        return redact_prediction_result_fields(row_data)
    return dict(row_data)


def resolve_prediction_request_safety(
    conn: Any,
    *,
    lottery_type: Any = "",
    year: Any = "",
    term: Any = "",
    res_code: Any = "",
) -> tuple[str | None, dict[str, Any]]:
    """检查预测请求是否允许携带 res_code 参与算法。

    若目标期次已开奖，则拒绝携带 res_code（返回 None），防止利用已知结果作弊；
    若未开奖，则正常传入 res_code。
    """
    normalized_res_code = str(res_code or "").strip() or ""
    visibility = lookup_draw_visibility(
        conn,
        lottery_type=lottery_type,
        year=year,
        term=term,
    )
    if visibility.get("result_visibility") == "hidden":
        return None, visibility
    return normalized_res_code or None, visibility
