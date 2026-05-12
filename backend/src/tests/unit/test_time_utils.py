"""core/time_utils.py 单元测试。"""

from __future__ import annotations

from core.time_utils import (
    utc_now_text,
    parse_hhmm,
    validate_hhmm,
    BEIJING_TZ,
)


def test_utc_now_text_returns_iso_format():
    result = utc_now_text()
    assert "T" in result
    assert len(result) >= 20


def test_parse_hhmm_valid():
    assert parse_hhmm("21:30") == (21, 30)
    assert parse_hhmm("09:00") == (9, 0)
    assert parse_hhmm("0:00") == (0, 0)
    assert parse_hhmm("23:59") == (23, 59)


def test_parse_hhmm_invalid():
    assert parse_hhmm("") is None
    assert parse_hhmm("abc") is None
    assert parse_hhmm("24:00") is None
    assert parse_hhmm("12:60") is None
    assert parse_hhmm("12:30:00") is None


def test_validate_hhmm():
    assert validate_hhmm("21:30") is True
    assert validate_hhmm("invalid") is False
    assert validate_hhmm("") is False


def test_beijing_tz_utc_offset():
    """北京时区偏移为 UTC+8。"""
    from datetime import timedelta
    assert BEIJING_TZ.utcoffset(None) == timedelta(hours=8)
