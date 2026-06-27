"""
Admin 预测管理 —— 模块同步 / 生成 / 批量操作 / 安全控制。

提供以下核心能力：
- 站点预测模块的同步与蓝图查询
- 预测行数据的构建与规范化
- 开奖可见性安全控制（防止未开奖期次泄露号码）
- 预测 API 响应构建
- 期号范围解析与已开奖数据查询
- 批量生成预测数据

从 app.py 提取，不改变任何函数签名与行为。
"""
from __future__ import annotations

from typing import Any

from domains.prediction import api_response as _prediction_api_response
from prediction_generation import service as _prediction_generation_service

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
from domains.prediction.result_fields import compute_res_fields  # noqa: F401 - 兼容导出







build_prediction_api_response = _prediction_api_response.build_prediction_api_response
normalize_prediction_display_text = _prediction_api_response.normalize_prediction_display_text


list_opened_draws_in_issue_range = _prediction_generation_service.list_opened_draws_in_issue_range

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
