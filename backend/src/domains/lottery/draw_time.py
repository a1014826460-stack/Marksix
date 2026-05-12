"""开奖时间计算工具。

统一处理开奖时间的解析、校验、下一期推算，
避免 crawler、public、prediction_generation 中各自实现。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from core.time_utils import BEIJING_TZ, parse_hhmm, validate_hhmm


def get_default_draw_time(lottery_type_id: int) -> str:
    """获取彩种默认开奖时间（HH:MM 格式）。

    Args:
        lottery_type_id: 彩种 ID（1=香港, 2=澳门, 3=台湾）

    Returns:
        默认开奖时间字符串。
    """
    defaults = {1: "21:30", 2: "21:00", 3: "22:30"}
    return defaults.get(lottery_type_id, "21:30")


def parse_draw_datetime(draw_time_str: str) -> datetime | None:
    """解析开奖时间字符串为北京时间 datetime。

    Args:
        draw_time_str: 开奖时间字符串，格式 "YYYY-MM-DD HH:MM:SS"。

    Returns:
        北京时间 datetime 对象；解析失败返回 None。
    """
    try:
        dt = datetime.strptime(str(draw_time_str).strip(), "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=BEIJING_TZ)
    except (ValueError, TypeError):
        return None


def is_draw_time_passed(draw_time_str: str) -> bool:
    """判断开奖时间是否已过（使用北京时间比较）。

    Args:
        draw_time_str: 开奖时间字符串 "YYYY-MM-DD HH:MM:SS"。

    Returns:
        True 如果当前北京时间已超过开奖时间。
    """
    draw_dt = parse_draw_datetime(draw_time_str)
    if draw_dt is None:
        return False
    now_beijing = datetime.now(BEIJING_TZ)
    return draw_dt <= now_beijing


def get_next_draw_time(draw_time_str: str) -> str:
    """根据当前开奖时间推算下一期开奖时间（+1天）。

    Args:
        draw_time_str: 当前期开奖时间 "YYYY-MM-DD HH:MM:SS"。

    Returns:
        下一期开奖时间字符串。
    """
    draw_dt = parse_draw_datetime(draw_time_str)
    if draw_dt is None:
        return ""
    next_dt = draw_dt + timedelta(days=1)
    return next_dt.strftime("%Y-%m-%d %H:%M:%S")


def validate_numbers(numbers: str) -> tuple[bool, str]:
    """校验开奖号码格式：恰好 7 个号码，每个在 01-49 范围内。

    Returns:
        (is_valid, error_message)
    """
    if not numbers or not numbers.strip():
        return False, "开奖号码不能为空"
    num_list = [n.strip() for n in numbers.split(",") if n.strip()]
    if len(num_list) != 7:
        return False, f"开奖号码必须恰好 7 个，当前 {len(num_list)} 个"
    for n in num_list:
        if not n.isdigit() or int(n) < 1 or int(n) > 49:
            return False, f"无效号码: {n}，每个号码必须为 01-49"
    return True, ""
