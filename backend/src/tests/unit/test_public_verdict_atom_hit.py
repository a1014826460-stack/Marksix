"""判定口径契约：小词标签（单/双/大/小/N头）不得被子串误匹配成命中。

后端 ``public/api.py::_check_correct_by_mechanism`` 对标准 contains/excludes 走的是
``label in outcome`` 子串判定，而 outcome 是 ``|`` 分隔的复合标签串。于是：

- 单双中特预测「单」，outcome 里的 `合单` / `3头单` / `单数` 都会让 `单` 命中；
- 大小中特预测「小」，outcome 里的 `合数小` / `小数` 同理；
- 中头玩法预测「1头」，outcome 里的 `1头单` / `1头双` 都会让 `1头` 命中。

这些行在页面上会显示「准」，但真实特码其实不在候选项里（虚报命中）。
本契约要求这些机制改用原子判定：真实结果原子必须与候选标签精确相等。
"""
from __future__ import annotations

import pytest

from predict.common import exact_contains_hit, excludes_hit_exact
from predict.mechanisms import PREDICTION_CONFIGS
from public.api import serialize_public_history_row

#: 274 期形状：特码 36（双 / 大 / 3头）
ROW_ODD_TAIL = {
    "year": "2026",
    "term": "274",
    "res_code": "01,14,23,30,37,46,36",
    "res_sx": "蛇,蛇,马,牛,鼠,鸡,羊",
    "res_color": "red,blue,red,blue,red,blue,red",
    "draw_is_opened": 1,
}

#: 274 期形状：特码 08（双 / 小 / 0头）
ROW_SMALL = {
    "year": "2026",
    "term": "274",
    "res_code": "21,39,42,02,18,17,08",
    "res_sx": "狗,龙,牛,蛇,牛,虎,猪",
    "res_color": "blue,blue,red,red,red,green,red",
    "draw_is_opened": 1,
}


def _row(base: dict[str, object], content: str) -> dict[str, object]:
    return {**base, "content": content}


# ── 单元：原子判定本身 ─────────────────────────────────────────


def test_exact_contains_hit_matches_atoms_only():
    outcome = "双数|大数|双|大|3头|3头双|6尾|6|蓝波|合单|合数大|野兽|羊|36|土|画|6段"

    # 原子成员命中
    assert exact_contains_hit(outcome, ("双",)) is True
    assert exact_contains_hit(outcome, ("大",)) is True
    assert exact_contains_hit(outcome, ("3头",)) is True
    assert exact_contains_hit(outcome, ("36",)) is True

    # 子串相似但不是同一个原子 → 不得命中
    assert exact_contains_hit(outcome, ("单",)) is False   # 合单 ≠ 单
    assert exact_contains_hit(outcome, ("小",)) is False   # 合数小 ≠ 小
    assert exact_contains_hit(outcome, ("4头",)) is False  # 无 4头


def test_excludes_hit_exact_is_the_inverse():
    outcome = "双|合单|3头双"
    assert excludes_hit_exact(outcome, ("单",)) is True
    assert excludes_hit_exact(outcome, ("双",)) is False


# ── 契约：受影响机制必须切到原子判定 ───────────────────────────


@pytest.mark.parametrize(
    "key, mode_id",
    [
        ("danshuangtema", 28),
        ("daxiao", 57),
        ("dxztt1", 108),
        ("3tou", 12),
        ("liangtouzxt", 471),
        ("sitouzhongte", 483),
    ],
)
def test_affected_mechanisms_use_exact_hit_checker(key: str, mode_id: int):
    config = PREDICTION_CONFIGS[key]

    assert int(config.default_modes_id) == mode_id
    assert config.hit_checker is exact_contains_hit, (
        f"{key} 必须使用原子判定，否则 `单`/`大`/`N头` 会被 outcome 子串误匹配"
    )


def test_danshuang_does_not_report_hit_for_the_opposite_parity():
    """特码 36 是双数；候选「单」不得被判成命中。"""
    config = PREDICTION_CONFIGS["danshuangtema"]

    assert serialize_public_history_row(
        _row(ROW_ODD_TAIL, "单|01,03,05,07,09,11"), config
    )["is_correct"] is False
    assert serialize_public_history_row(
        _row(ROW_ODD_TAIL, "双|02,04,06,08,10,12"), config
    )["is_correct"] is True


def test_daxiao_does_not_report_hit_for_the_opposite_size():
    """特码 08 是小；候选「大」不得被判成命中。"""
    config = PREDICTION_CONFIGS["daxiao"]

    assert serialize_public_history_row(
        _row(ROW_SMALL, '["大|25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49"]'),
        config,
    )["is_correct"] is False
    assert serialize_public_history_row(
        _row(ROW_SMALL, '["小|01,02,03,04,05,06,07,08,09,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24"]'),
        config,
    )["is_correct"] is True


def test_tou_mechanism_requires_the_exact_head():
    """特码 36 是 3 头；候选「4头」不得被判成命中。"""
    config = PREDICTION_CONFIGS["sitouzhongte"]

    assert serialize_public_history_row(
        _row(ROW_ODD_TAIL, '["4头|40,41,42,43,44,45,46,47,48,49"]'), config
    )["is_correct"] is False
    assert serialize_public_history_row(
        _row(ROW_ODD_TAIL, '["3头|30,31,32,33,34,35,36,37,38,39"]'), config
    )["is_correct"] is True
