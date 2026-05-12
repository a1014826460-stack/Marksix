"""统一时间工具：UTC 时间、北京时区转换、开奖时间处理。

把原来散落在 db.py、helpers.py、crawler、public、prediction_generation
中的时间处理逻辑统一放在这里，避免各模块各写一套。
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

# 北京时区（UTC+8），Python 3.9+ 可用 timezone(timedelta(hours=8))
BEIJING_TZ = timezone(timedelta(hours=8))

# HH:MM 格式校验正则
_HHMM_PATTERN = re.compile(r"^\d{1,2}:\d{2}$")


def utc_now_text() -> str:
    """返回当前 UTC 时间的 ISO 8601 字符串。

    用于数据库时间戳、日志记录等场景。
    """
    return datetime.now(timezone.utc).isoformat()


def utc_now() -> str:
    """返回当前 UTC 时间的 ISO 8601 字符串（别名，兼容旧代码）。"""
    return utc_now_text()


def beijing_now() -> datetime:
    """返回当前北京时间（UTC+8）的 datetime 对象。"""
    return datetime.now(BEIJING_TZ)


def beijing_now_text() -> str:
    """返回当前北京时间（UTC+8）的 ISO 8601 字符串。"""
    return datetime.now(BEIJING_TZ).isoformat()


def parse_hhmm(value: str) -> tuple[int, int] | None:
    """解析 HH:MM 格式时间字符串，返回 (hour, minute) 或 None。

    Args:
        value: 时间字符串，如 "21:30"、"09:00"。

    Returns:
        解析成功返回 (小时, 分钟) 元组，失败返回 None。
    """
    if not value or not _HHMM_PATTERN.match(str(value).strip()):
        return None
    parts = str(value).strip().split(":")
    try:
        hour, minute = int(parts[0]), int(parts[1])
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
    except (ValueError, IndexError):
        pass
    return None


def validate_hhmm(value: str) -> bool:
    """校验是否为合法的 HH:MM 格式时间字符串。"""
    return parse_hhmm(value) is not None


def combine_draw_datetime(date_str: str, hhmm: str) -> datetime | None:
    """将日期字符串与 HH:MM 时间组合为北京时间 datetime。

    用于爬虫调度中，把开奖日期与开奖时间（如 "21:30"）合并为完整的开奖时刻。

    Args:
        date_str: 日期字符串，格式 "YYYY-MM-DD"。
        hhmm: 时间字符串，格式 "HH:MM"。

    Returns:
        北京时间 datetime 对象；解析失败返回 None。
    """
    parsed_time = parse_hhmm(hhmm)
    if parsed_time is None:
        return None
    try:
        date_part = datetime.strptime(str(date_str).strip()[:10], "%Y-%m-%d")
        return date_part.replace(
            hour=parsed_time[0],
            minute=parsed_time[1],
            second=0,
            microsecond=0,
            tzinfo=BEIJING_TZ,
        )
    except (ValueError, TypeError):
        return None


def beijing_to_utc(dt: datetime) -> datetime:
    """北京时间 datetime 转为 UTC datetime。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BEIJING_TZ)
    return dt.astimezone(timezone.utc)


def utc_to_beijing(dt: datetime) -> datetime:
    """UTC datetime 转为北京时间 datetime。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BEIJING_TZ)


def beijing_now_iso() -> str:
    """返回当前北京时间的 ISO 8601 格式字符串。"""
    return beijing_now().isoformat()
