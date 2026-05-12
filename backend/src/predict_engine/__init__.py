"""predict_engine/ 预测引擎层 —— 纯算法，不感知 HTTP、用户、站点权限。

当前阶段从 predict/ 包重导出，后续逐步将实现迁移到此目录。
"""

from __future__ import annotations

# ── 兼容重导出：从 predict/ 包导入核心符号 ──
from predict.common import (  # noqa: F401
    predict,
    load_history,
    score_labels,
    PredictionConfig,
    parse_res_code,
    load_fixed_value_map,
    historical_content_hit_rate,
    build_element_number_map,
)
from predict.mechanisms import (  # noqa: F401
    list_prediction_configs,
    get_prediction_config,
    set_mechanism_status,
    ensure_prediction_configs_loaded,
    PREDICTION_CONFIGS,
)
