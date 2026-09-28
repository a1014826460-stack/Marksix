"""平特尾（``flat_tail``）多尾标签口径契约：一个标签里的多个尾原子都要参与判定。

背景（2026-09-29，生产库 `--limit 200` 深扫）
--------------------------------------------
供应商正文会把平特一尾的候选写成一个逗号串：``["9尾,4尾,3尾,7尾,8尾,0尾,1尾|"]``
（mode 54 / `pt1wei`，twbst528、twjsz666、twwanli 等站的深层历史行共 24 行）。

* 规则（`predict.common.flat_tail_hit` 的 docstring / 站点文案）：平特尾是
  「开奖 7 个号码的尾数集合 ∩ 预测尾集合 ≠ ∅」，所以逗号串里的**每个** `N尾`
  都必须参与判定。
* 修复前 ``_tail_digits`` 收到 *tuple* 时对每个元素整串只做一次 ``re.search``，
  于是 ``("1尾,3尾,5尾",)`` 只得到 ``{"1"}``：第一个尾不中、后面某个尾命中的期次
  会被判「错」（展示层漏判）。

本测试钉死修复后的口径，同时锁住既有行为（单个尾标签、纯号码取末位）不回退。
"""
from __future__ import annotations

import pytest

from predict.common import _tail_digits, flat_tail_hit


def test_multi_tail_label_exposes_every_tail_atom():
    assert _tail_digits(("1尾,3尾,5尾",)) == {"1", "3", "5"}


def test_tuple_and_string_forms_agree():
    """同一份尾集合，写成元组（候选标签）或字符串（outcome）必须等价。"""
    assert _tail_digits(("1尾,3尾,5尾",)) == _tail_digits("1尾,3尾,5尾")
    assert _tail_digits(("9尾,4尾,3尾,7尾,8尾,0尾,1尾",)) == _tail_digits(
        "9尾,4尾,3尾,7尾,8尾,0尾,1尾"
    )


@pytest.mark.parametrize(
    ("outcome_tails", "labels", "expected"),
    [
        # 修复前会漏判：只有第一个尾(1)不中，5 尾中 → 必须判命中
        ("0尾,2尾,5尾,6尾,7尾,8尾,9尾", ("1尾,3尾,5尾",), True),
        # 修复前同样漏判：第一个尾(1)不中，9 尾中
        ("0尾,2尾,4尾,6尾,7尾,8尾,9尾", ("1尾,3尾,9尾",), True),
        # 整串都不中 → 仍然「错」（不是把判定放宽成恒真）
        ("0尾,2尾,4尾,6尾,7尾,8尾,9尾", ("1尾,3尾,5尾",), False),
        # 第一个尾就中 → 前后一致
        ("1尾,3尾,5尾,6尾,7尾,8尾,9尾", ("1尾,3尾,5尾",), True),
        # 单个尾标签（供应商常见形态）行为不变
        ("1尾,3尾,5尾,6尾,7尾,8尾,9尾", ("5尾",), True),
        ("1尾,3尾,5尾,6尾,7尾,8尾,9尾", ("4尾",), False),
    ],
)
def test_flat_tail_hit_uses_all_tail_atoms(outcome_tails, labels, expected):
    assert flat_tail_hit(outcome_tails, labels) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # 纯号码取末位：13 → 3
        (("13",), {"3"}),
        (("1",), {"1"}),
        # `|` / 中文顿号 / 分号 / 斜杠都算分隔符
        (("1尾|3尾,5尾",), {"1", "3", "5"}),
        (("1尾、3尾",), {"1", "3"}),
        # 非尾内容不产出尾数字之外的东西（分组名等）
        (("后落码",), set()),
    ],
)
def test_tail_digit_normalization_keeps_existing_behaviour(value, expected):
    assert _tail_digits(value) == expected
