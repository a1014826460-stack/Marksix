"""判定口径契约：「三头四尾」与「半波类」玩法的 is_correct 复算。

背景（2026-09-28 线上实测）
--------------------------
1. twjsz666(web 11) `#yxym` 容器「三头四尾」(mode 492) 连续 8 期全部显示「错」。
   根因：``public/api.py::_check_correct_by_mechanism`` 把 ``_compute_outcome_from_row``
   的**通用复合串**喂给了机制专属 hit_checker ``three_head_four_tail_hit``，而它要求
   ``头:3头|尾:7尾`` 的每一段都出现在候选里；通用串里的 ``双数``/``大数``/``蓝波`` 等
   永远不在候选集合内 → 判定恒为 False。

   口径（2026-09-28 钉死）：三头四尾是 ``PredictionCategory.MIXED``（标签带 `头:`/`尾:`
   两个维度前缀），按 ``backend/CLAUDE.md``「MIXED 的业务命中语义为任一维度命中即算命中」
   与 ``mixed_dimension_contains_hit`` 一致 —— **特码头或特码尾任一落入对应候选即命中**。
   供应商静态样本同口径（053期 `三头【4.1.3】四尾【1.4.9.2】开09鸡对`：只有尾命中仍标「对」）。

2. 半波玩法（mode 58 绝杀半波 / mode 490 杀两半波）候选标签是 ``蓝双`` 这类两字半波标签，
   而通用复合串只提供 ``蓝波`` 与 ``双``，``蓝双`` 不是任何原子的子串 →
   ``excludes_hit`` 恒等于 True，判定写死「对」。
   修法是把半波原子补进通用复合串（与 ``fixed_data`` 的 ``波色单双`` 映射一致）。
"""
from __future__ import annotations

import pytest

from predict.common import table_exists
from predict.mechanisms import PREDICTION_CONFIGS
from public.api import (
    _check_correct_by_mechanism,
    _compute_outcome_from_row,
    _mechanism_outcome_from_row,
    serialize_public_history_row,
)

#: 2026-222 期（本地库同形状）：特码 26 → 2头 / 6尾 / 蓝波 / 蓝双
ROW_SPECIAL_26 = {
    "year": "2026",
    "term": "222",
    "res_code": "49,14,47,27,18,38,26",
    "res_sx": "蛇,蛇,马,牛,鼠,鸡,蛇",
    "res_color": "green,green,red,blue,green,blue,blue",
    "draw_is_opened": 1,
}

#: 2026-216 期：特码 37 → 3头 / 7尾 / 蓝波 / 蓝单
ROW_SPECIAL_37 = {
    "year": "2026",
    "term": "216",
    "res_code": "18,41,32,44,36,45,37",
    "res_sx": "鼠,羊,龙,鼠,猪,狗,马",
    "res_color": "blue,green,green,green,green,red,blue",
    "draw_is_opened": 1,
}

ROW_PENDING = {
    "year": "2026",
    "term": "271",
    "res_code": "",
    "res_sx": "",
    "res_color": "",
    "draw_is_opened": 0,
}

#: 供应商标准波色映射（与 public.fixed_data `波色` 一致），用于独立复算半波。
WAVE_BY_CODE: dict[str, str] = {}
for _code in "01,02,07,08,12,13,18,19,23,24,29,30,34,35,40,45,46".split(","):
    WAVE_BY_CODE[_code] = "红波"
for _code in "03,04,09,10,14,15,20,25,26,31,36,37,41,42,47,48".split(","):
    WAVE_BY_CODE[_code] = "蓝波"
for _code in "05,06,11,16,17,21,22,27,28,32,33,38,39,43,44,49".split(","):
    WAVE_BY_CODE[_code] = "绿波"


def _row(base: dict[str, object], content: str) -> dict[str, object]:
    return {**base, "content": content}


# ── 三头四尾（mode 492）─────────────────────────────────────────


def test_three_head_four_tail_outcome_contract_is_head_and_tail():
    """机制专属 outcome 是 `头:X|尾:Y`；通用复合串不满足这个契约（旧缺陷根源）。"""
    config = PREDICTION_CONFIGS["three_head_four_tail"]
    content = '{"heads":["2头","4头","1头"],"tails":["6尾","8尾","4尾","3尾"]}'
    labels = config.content_parser(content)

    assert _mechanism_outcome_from_row(config, _row(ROW_SPECIAL_26, content)) == "头:2头|尾:6尾"
    assert config.hit_checker("头:2头|尾:6尾", labels) is True
    # 通用复合串（旧实现传给 checker 的东西）里的原子与 `头:/尾:` 候选标签不同空间
    assert config.hit_checker(_compute_outcome_from_row(_row(ROW_SPECIAL_26, content)), labels) is False


def test_three_head_four_tail_hits_when_any_dimension_hits():
    config = PREDICTION_CONFIGS["three_head_four_tail"]

    # 头、尾都命中 → 对
    both = _row(ROW_SPECIAL_26, '{"heads":["2头","4头","1头"],"tails":["6尾","8尾","4尾","3尾"]}')
    assert serialize_public_history_row(both, config)["is_correct"] is True

    # 只有头命中（6尾 不在候选）→ 对（MIXED 任一维度命中口径）
    head_only = _row(ROW_SPECIAL_26, '{"heads":["2头","4头","1头"],"tails":["0尾","1尾","5尾","9尾"]}')
    assert serialize_public_history_row(head_only, config)["is_correct"] is True

    # 只有尾命中（2头 不在候选）→ 对
    tail_only = _row(ROW_SPECIAL_26, '{"heads":["0头","3头","4头"],"tails":["6尾","8尾","4尾","3尾"]}')
    assert serialize_public_history_row(tail_only, config)["is_correct"] is True

    # 两个维度都没命中 → 错
    neither = _row(ROW_SPECIAL_26, '{"heads":["0头","3头","4头"],"tails":["0尾","1尾","5尾","9尾"]}')
    assert serialize_public_history_row(neither, config)["is_correct"] is False


def test_three_head_four_tail_pending_row_has_no_verdict():
    config = PREDICTION_CONFIGS["three_head_four_tail"]
    row = _row(ROW_PENDING, '{"heads":["2头","4头","1头"],"tails":["6尾","8尾","4尾","3尾"]}')
    serialized = serialize_public_history_row(row, config)

    assert serialized["is_opened"] is False
    assert serialized["is_correct"] is None


def test_three_head_four_tail_works_without_a_database_connection():
    """没有 conn 时 fixed_data 兜底不可用，头/尾标签必须退化为等价的数字标签。"""
    config = PREDICTION_CONFIGS["three_head_four_tail"]
    content = '{"heads":["2头","4头","1头"],"tails":["6尾","8尾","4尾","3尾"]}'
    row = _row(ROW_SPECIAL_26, content)

    assert _mechanism_outcome_from_row(config, row) == "头:2头|尾:6尾"
    assert _check_correct_by_mechanism(content, row, config) is True


def test_table_exists_is_safe_without_a_connection():
    assert table_exists(None, "fixed_data") is False


# ── 半波（mode 58 / 490）────────────────────────────────────────


def test_outcome_carries_half_wave_atoms_for_every_number():
    """01-49 每个号码的通用复合串都必须带与 `波色单双` 一致的半波原子。"""
    color_of = {"红波": "red", "蓝波": "blue", "绿波": "green"}
    for value in range(1, 50):
        code = f"{value:02d}"
        wave = WAVE_BY_CODE[code]
        row = {
            "year": "2026",
            "term": "999",
            "res_code": f"01,02,03,04,05,06,{code}",
            "res_sx": "鼠,牛,虎,兔,龙,蛇,马",
            "res_color": "red,red,red,red,red,red," + color_of[wave],
            "draw_is_opened": 1,
        }
        expected = f"{wave.removesuffix('波')}{'双' if value % 2 == 0 else '单'}"
        atoms = _compute_outcome_from_row(row).split("|")

        assert wave in atoms, f"{code} 缺少波色原子"
        assert expected in atoms, f"{code} 缺少半波原子 {expected}"


@pytest.mark.parametrize("key, mode_id", [("jueshabanbo", 58), ("shaliangbanbo", 490)])
def test_half_wave_exclusion_uses_real_half_wave_labels(key: str, mode_id: int):
    config = PREDICTION_CONFIGS[key]

    assert int(config.default_modes_id) == mode_id

    # 26 是蓝双：候选里含「蓝双」必须判「错」（排除项命中特码）
    assert serialize_public_history_row(
        _row(ROW_SPECIAL_26, "蓝双,蓝单"), config
    )["is_correct"] is False
    # 26 是蓝双：候选里不含它 → 「对」
    assert serialize_public_history_row(
        _row(ROW_SPECIAL_26, "红双,绿双"), config
    )["is_correct"] is True
    # 37 是蓝单
    assert serialize_public_history_row(
        _row(ROW_SPECIAL_37, "红双,蓝单"), config
    )["is_correct"] is False
    assert serialize_public_history_row(
        _row(ROW_SPECIAL_37, "蓝双,绿单"), config
    )["is_correct"] is True


def test_half_wave_exclusion_pending_row_has_no_verdict():
    config = PREDICTION_CONFIGS["shaliangbanbo"]
    row = _row(ROW_PENDING, "蓝双,蓝单")
    assert serialize_public_history_row(row, config)["is_correct"] is None
