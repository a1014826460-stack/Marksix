from __future__ import annotations

from predict.mechanisms import PREDICTION_CONFIGS
from public.api import serialize_public_history_row


def _row(content: str) -> dict[str, object]:
    """265 期真实资料形状：7 个号码，特码 08=猪，平码里含 蛇。"""
    return {
        "year": "2026",
        "term": "265",
        "res_code": "21,39,42,02,18,17,08",
        "res_sx": "狗,龙,牛,蛇,牛,虎,猪",
        "res_color": "blue,blue,red,red,red,green,red",
        "content": content,
        "draw_is_opened": 1,
    }


def test_flat_one_xiao_hits_when_any_drawn_number_matches_the_zodiac():
    config = PREDICTION_CONFIGS["pt1xiao"]
    assert config.flat_zodiac is True

    result = serialize_public_history_row(_row("蛇"), config)

    assert result["is_opened"] is True
    assert result["result_text"] == "猪08"
    # 蛇不是特码生肖（特码是猪），但出现在平码里，平特一肖算命中。
    assert result["is_correct"] is True


def test_flat_one_xiao_misses_when_no_drawn_number_matches_the_zodiac():
    config = PREDICTION_CONFIGS["pt1xiao"]

    result = serialize_public_history_row(_row("马"), config)

    assert result["is_correct"] is False


def test_flat_one_xiao_hits_when_the_special_zodiac_matches():
    config = PREDICTION_CONFIGS["pt1xiao"]

    assert serialize_public_history_row(_row("猪"), config)["is_correct"] is True


def test_non_flat_zodiac_module_still_judges_by_the_special_zodiac():
    config = PREDICTION_CONFIGS["3zxt"]
    assert config.flat_zodiac is False

    # 蛇在平码里、不是特码；三肖中特仍按特码生肖判定，因此不算命中。
    assert serialize_public_history_row(_row("蛇,马,羊"), config)["is_correct"] is False
    assert serialize_public_history_row(_row("猪,马,羊"), config)["is_correct"] is True
