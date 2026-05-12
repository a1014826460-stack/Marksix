"""预测运行器 —— 封装单次预测的执行逻辑。

当前阶段委托给 predict.common 中的现有实现。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def run_prediction(
    *,
    mechanism_key: str,
    res_code: str | None = None,
    content: str | None = None,
    source_table: str | None = None,
    db_path: str | Path | None = None,
    target_hit_rate: float = 0.65,
) -> dict[str, Any]:
    """执行一次预测运算。

    Args:
        mechanism_key: 预测机制标识。
        res_code: 已知开奖结果（用于历史回填），未来预测不传。
        content: 自定义内容文本。
        source_table: 数据源表名。
        db_path: 数据库路径。
        target_hit_rate: 目标命中率。

    Returns:
        预测结果字典。
    """
    from predict.common import predict
    from predict.mechanisms import get_prediction_config

    config = get_prediction_config(mechanism_key)
    return predict(
        config=config,
        res_code=res_code,
        content=content,
        source_table=source_table,
        db_path=db_path or "",
        target_hit_rate=target_hit_rate,
    )
