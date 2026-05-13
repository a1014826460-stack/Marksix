"""预测数据重新生成服务。

提供单条预测数据的重新生成能力，包括参数校验、特码段数特殊处理、
通用 predict() 调用和持久化。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from db import connect, utc_now
from helpers import load_fixed_data_maps
from predict.common import predict
from predict.mechanisms import get_prediction_config
from runtime_config import get_config
from utils.created_prediction_store import (
    normalize_color_label,
    upsert_created_prediction_row,
)


def compute_res_fields(numbers_str: str, zodiac_map: dict, color_map: dict) -> tuple[str, str]:
    """根据开奖号码字符串计算 res_sx（生肖）和 res_color（波色）逗号分隔值。

    :param numbers_str: 逗号分隔的开奖号码字符串（如 "01,15,23,34,42,08,11"）
    :param zodiac_map: 号码 → 生肖映射字典
    :param color_map: 号码 → 波色映射字典
    :return: (res_sx, res_color) 元组，均为逗号分隔的字符串
    """
    res_sx_parts: list[str] = []
    res_color_parts: list[str] = []
    for num_str in (numbers_str or "").split(","):
        num_str = num_str.strip()
        if not num_str:
            continue
        try:
            num_zf = f"{int(num_str):02d}"
        except ValueError:
            continue
        res_sx_parts.append(str(zodiac_map.get(num_zf) or ""))
        res_color_parts.append(normalize_color_label(color_map.get(num_zf, "")))
    return (
        ",".join(res_sx_parts) if any(res_sx_parts) else "",
        ",".join(res_color_parts) if any(res_color_parts) else "",
    )


def regenerate_payload_data(
    db_path: str | Path,
    table_name: str,
    mechanism_key: str = "",
    res_code: str = "",
    lottery_type: str = "3",
    year: str = "",
    term: str = "",
    web_value: str = "",
) -> dict[str, Any]:
    """调用 predict() 生成新预测，覆盖 mode_payload 表中同彩种同期数的数据。

    用于后台"重新生成"单条预测数据的操作。对输入参数进行严格校验：
    - table_name 必须符合 ``mode_payload_{数字}`` 格式
    - res_code 必须为 7 个逗号分隔的数字
    - year 必须为 4 位数字
    - term 必须为 1-5 位数字且不为 0

    特殊处理：
    - mode_id=65（特码段数）：根据特码直接计算 12 个号码段，不调用 predict()
    """
    from admin.payload import validate_mode_payload_table as _validate

    table_name = _validate(table_name)
    mechanism_key = str(mechanism_key or "").strip()
    if not mechanism_key:
        raise ValueError("mechanism_key 不能为空")

    res_code = str(res_code or "").strip()
    if res_code:
        codes = [c.strip() for c in res_code.split(",") if c.strip()]
        if len(codes) != 7:
            raise ValueError("开奖号码必须为7个数字，逗号分隔。")
        for c in codes:
            if not re.fullmatch(r"\d{1,2}", c):
                raise ValueError(f"无效号码: {c}")

    year = str(year or "").strip()
    if year and not re.fullmatch(r"\d{4}", year):
        raise ValueError("年份必须为4位数字。")

    term = str(term or "").strip()
    if term and not re.fullmatch(r"\d{1,5}", term):
        raise ValueError("期数必须为1-5位数字。")
    if term and int(term) == 0:
        raise ValueError("期数不能为0。")

    web_value = str(web_value or "").strip()
    if not web_value:
        raise ValueError("web_value 不能为空")
    if not web_value.isdigit():
        raise ValueError("web_value 必须为整数")

    config = get_prediction_config(mechanism_key)
    mode_id = int(config.default_modes_id or 0)

    # ── mode_id=65 特码段数：根据特码生成连续12个号码段 ──
    if mode_id == 65:
        codes_list = [c.strip() for c in res_code.split(",") if c.strip()]
        try:
            special_code = int(codes_list[-1]) if codes_list else 0
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

        with connect(db_path) as conn:
            if not conn.table_exists(table_name):
                raise ValueError(f"表 {table_name} 不存在。")
            zodiac_map, color_map = load_fixed_data_maps(conn)
            columns = set(conn.table_columns(table_name))

            res_sx, res_color = compute_res_fields(res_code, zodiac_map, color_map)

            insert_data: dict[str, Any] = {
                "type": str(lottery_type),
                "year": str(year) if year else "",
                "term": str(term) if term else "",
                "web": web_value,
                "web_id": int(web_value),
                "modes_id": 65,
                "res_code": res_code,
                "res_sx": res_sx,
                "res_color": res_color,
                "content": content,
                "status": 1,
            }

            filtered_data = {k: v for k, v in insert_data.items() if k in columns}
            if not filtered_data:
                raise ValueError("生成的预测数据无法匹配目标表任何列。")

            stored = upsert_created_prediction_row(conn, table_name, filtered_data)
            return {
                "inserted_id": stored.get("id"),
                "action": stored.get("action"),
                "created_at": stored.get("created_at"),
                "prediction_labels": [],
                "content": content,
                "table": stored.get("table"),
                "qualified_table": stored.get("qualified_table"),
            }

    result = predict(
        config=config,
        res_code=res_code or None,
        source_table=table_name,
        db_path=db_path,
        target_hit_rate=float(get_config(db_path, "prediction.default_target_hit_rate", 0.65)),
    )

    generated_content = result["prediction"]["content"]
    prediction_labels = result["prediction"]["labels"]

    with connect(db_path) as conn:
        if not conn.table_exists(table_name):
            raise ValueError(f"表 {table_name} 不存在。")

        columns = set(conn.table_columns(table_name))

        insert_data: dict[str, Any] = {
            "type": str(lottery_type),
            "year": str(year) if year else "",
            "term": str(term) if term else "",
            "web": web_value,
            "web_id": int(web_value),
        }

        if res_code:
            insert_data["res_code"] = res_code

        if isinstance(generated_content, dict):
            for key, value in generated_content.items():
                if key == "_labels":
                    continue
                if key in columns:
                    insert_data[key] = value
        elif "content" in columns:
            insert_data["content"] = (
                str(generated_content)
                if isinstance(generated_content, str)
                else json.dumps(generated_content, ensure_ascii=False)
            )

        filtered_data = {k: v for k, v in insert_data.items() if k in columns}
        if not filtered_data:
            raise ValueError("生成的预测数据无法匹配目标表任何列。")

        stored = upsert_created_prediction_row(conn, table_name, filtered_data)

        return {
            "inserted_id": stored.get("id"),
            "action": stored.get("action"),
            "created_at": stored.get("created_at"),
            "prediction_labels": prediction_labels,
            "content": generated_content,
            "table": stored.get("table"),
            "qualified_table": stored.get("qualified_table"),
        }
