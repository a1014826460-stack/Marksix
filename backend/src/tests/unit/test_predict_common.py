"""predict/common.py 核心纯函数单元测试。

测试预测引擎中不依赖数据库的纯函数。
"""

from __future__ import annotations

from predict.common import parse_res_code
from utils.created_prediction_store import normalize_color_label


# ── parse_res_code ─────────────────────────────────────

def test_parse_res_code_valid():
    result = parse_res_code("01,02,03,04,05,06,07")
    assert result == ["01", "02", "03", "04", "05", "06", "07"]


def test_parse_res_code_with_spaces():
    result = parse_res_code("01, 02, 03, 04, 05, 06, 07")
    assert "01" in result
    assert len(result) == 7


def test_parse_res_code_empty_raises():
    """空字符串会抛出 ValueError。"""
    try:
        parse_res_code("")
        assert False, "should raise"
    except ValueError:
        pass


def test_parse_res_code_single():
    result = parse_res_code("42")
    assert result == ["42"]


# ── normalize_color_label ──────────────────────────────

def test_normalize_color_label_red():
    assert normalize_color_label("red") == "red"
    assert normalize_color_label("红") == "red"


def test_normalize_color_label_blue():
    assert normalize_color_label("blue") == "blue"
    assert normalize_color_label("蓝") == "blue"


def test_normalize_color_label_green():
    assert normalize_color_label("green") == "green"
    assert normalize_color_label("绿") == "green"


def test_normalize_color_label_empty():
    result = normalize_color_label("")
    assert result == ""


def test_normalize_color_label_unknown():
    result = normalize_color_label("unknown_color")
    assert result == "unknown_color"
