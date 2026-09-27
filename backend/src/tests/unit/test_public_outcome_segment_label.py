"""公开页历史行的命中判定：段位标签必须进入 outcome，否则四段中特恒判「错」。

回归背景：`_compute_outcome_from_row` 覆盖了单双/大小/头/尾/波色/合数/家禽野兽/
生肖/号码/五行/四艺，却没有段位标签，导致 mode 479（四段中特）的
`is_correct` 永远是 False —— 269 期特码 46 明明落在预测的 7 段里也显示「错」。
"""

from __future__ import annotations

from public.api import _compute_outcome_from_row


def _row(code: str, zodiac: str = "马", color: str = "blue") -> dict[str, str]:
    return {
        "res_code": f"01,02,03,04,05,06,{code}",
        "res_sx": f"鼠,牛,虎,兔,龙,蛇,{zodiac}",
        "res_color": f"red,red,red,red,red,red,{color}",
    }


def test_outcome_contains_segment_label():
    outcome = _compute_outcome_from_row(_row("46"))

    assert "7段" in outcome.split("|"), "46 应落在 7 段"


def test_outcome_segment_for_boundary_numbers():
    assert f"{(1 - 1) // 7 + 1}段" in _compute_outcome_from_row(_row("01")).split("|")
    assert "1段" in _compute_outcome_from_row(_row("07")).split("|")
    assert "2段" in _compute_outcome_from_row(_row("08")).split("|")
    assert "7段" in _compute_outcome_from_row(_row("49")).split("|")


def test_four_segment_mechanism_hit_is_true_when_special_in_prediction():
    """四段中特 269 期：预测 [4段,3段,2段,7段]，特码 46 落在 7 段 -> 命中。"""
    from predict.mechanisms import PREDICTION_CONFIGS
    from public.api import _check_correct_by_mechanism

    config = PREDICTION_CONFIGS["siduanzhongte"]
    prediction = '["4段|22,23,24,25,26,27,28","3段|15,16,17,18,19,20,21",' \
                 '"2段|08,09,10,11,12,13,14","7段|43,44,45,46,47,48,49"]'

    assert _check_correct_by_mechanism(prediction, _row("46"), config) is True


def test_four_segment_mechanism_miss_is_false():
    from predict.mechanisms import PREDICTION_CONFIGS
    from public.api import _check_correct_by_mechanism

    config = PREDICTION_CONFIGS["siduanzhongte"]
    prediction = '["3段|15,16,17,18,19,20,21","2段|08,09,10,11,12,13,14",' \
                 '"1段|01,02,03,04,05,06,07","4段|22,23,24,25,26,27,28"]'

    # 特码 37 落在 6 段，不在预测的四段里
    assert _check_correct_by_mechanism(prediction, _row("37"), config) is False
