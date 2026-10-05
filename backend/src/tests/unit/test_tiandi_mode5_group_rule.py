"""天地生肖（mode 5）受控规则与正文契约。

背景（2026-10-05 用户反馈「为什么都是天肖」）：

- mode 5 过去挂在 `content+xiao` 玩法上，分组由 `format_content_xiao_columns` 从
  **历史 content 池按出现次数降序**里挑「与预测两肖不重叠」的第一条，兜底再取出现最多的
  那条 → 分组被历史众数锁死。线上 twsaimahui 269–278 期 10/10 全「天肖」，同期特肖
  是 4 天 5 地（命中 4/9 ≈ 固定押天肖的期望值），说明分组从未被预测。
- 修正后与 mode 155（吉美凶丑）/133（前后生肖）同构：候选 = 分组名，真实目标 =
  特肖所属分组（`fixed_data` sign='天地生肖'），正文 = `分组名|成员生肖`，
  第二维 `xiao` 槽取该分组内的两肖（恒为分组子集，两个判定口径永远同向）。
"""

from __future__ import annotations

import pytest

from domains.prediction.generation_rules import RULE_BY_MODE_ID
from domains.prediction.models import DrawTruth
from predict.mechanisms import (
    PREDICTION_CONFIGS,
    TIANDI_LABELS,
    TIANDI_XIAO_WIDTH,
    format_tiandi_groups,
    group_label_for_zodiac,
    special_tiandi_from_row,
    TIANDI_LABEL_FALLBACK,
)


def _truth(zodiac: str, code: str = "37") -> DrawTruth:
    return DrawTruth(numbers=(), special_code=code, special_zodiac=zodiac)


def _config():
    return PREDICTION_CONFIGS["title_5"]


# ── 候选域与口径 ────────────────────────────────────────────────────────────

def test_mode5_candidate_domain_is_the_group_labels():
    config = _config()
    assert config.default_modes_id == 5
    assert config.labels == TIANDI_LABELS == ("天肖", "地肖")
    assert config.label_count == 1
    assert config.hit_checker is not None
    # 判定必须读正文（分组），不再读 xiao（两肖）——否则口径又回到「仅两肖」
    assert config.content_loader is not None


def test_tiandi_truth_outcome_is_the_group_label():
    assert special_tiandi_from_row({"res_sx": "羊", "res_code": "01,02,03,04,05,06,12"}, None) == "地肖"
    assert special_tiandi_from_row({"res_sx": "马", "res_code": "01,02,03,04,05,06,37"}, None) == "天肖"
    # 12 生肖必须恰好落在两组之一，且两组互斥
    from predict.common import ZODIAC_ORDER

    seen = {}
    for zodiac in ZODIAC_ORDER:
        label = group_label_for_zodiac(zodiac, {}, TIANDI_LABELS, TIANDI_LABEL_FALLBACK)
        assert label in TIANDI_LABELS, zodiac
        assert zodiac not in seen, f"{zodiac} 同时属于两组"
        seen[zodiac] = label
    assert sorted(seen.values()) == ["地肖"] * 6 + ["天肖"] * 6


# ── 受控规则 ────────────────────────────────────────────────────────────────

def test_mode5_registers_a_controlled_group_rule():
    rule = RULE_BY_MODE_ID[5]
    assert rule.supported is True
    assert rule.rule_id == "zodiac_group"
    assert rule.truth_outcome is not None
    assert rule.truth_outcome(_truth("羊"), None) == "地肖"
    assert rule.truth_outcome(_truth("龙"), None) == "天肖"
    # 命中方向：候选分组包含真实特肖 → 命中
    config = _config()
    assert rule.verify_hit(config, ("地肖",), _truth("羊"), conn=None) is True
    assert rule.verify_hit(config, ("天肖",), _truth("羊"), conn=None) is False
    assert rule.verify_hit(config, ("天肖",), _truth("马"), conn=None) is True
    assert rule.verify_hit(config, ("地肖",), _truth("马"), conn=None) is False


def test_mode5_has_no_truth_zodiac_when_unopened():
    """未开奖/缺特肖时真实目标为空，规则不得凭空命中。"""
    rule = RULE_BY_MODE_ID[5]
    assert rule.truth_outcome(_truth(""), None) == ""
    assert rule.verify_hit(_config(), ("天肖",), _truth(""), conn=None) is False


def test_controlled_generation_can_only_target_a_group_of_the_real_zodiac():
    """受控生成的可选标签只有两个分组，而规则目标 = 真实特肖所属分组。

    `candidate_control.label_for_truth_outcome()` 会用 `outcome_loader` 从真实
    DrawTruth 反解目标标签（需要真实连接去查号码→生肖表，因此这里直接验证规则本身），
    目标必然落在候选域 `("天肖","地肖")` 内 —— 旧实现「按历史 content 出现次数挑分组」
    的频率锁死路径已经不存在。
    """
    config = _config()
    rule = RULE_BY_MODE_ID[5]
    assert {"天肖", "地肖"} == set(config.labels)
    for zodiac, expected in (("羊", "地肖"), ("鼠", "地肖"), ("马", "天肖"), ("龙", "天肖")):
        assert rule.truth_outcome(_truth(zodiac), None) == expected
        assert rule.verify_hit(config, (expected,), _truth(zodiac), conn=None) is True
        other = "天肖" if expected == "地肖" else "地肖"
        assert rule.verify_hit(config, (other,), _truth(zodiac), conn=None) is False


# ── 正文形态（不再依赖历史 content 池）────────────────────────────────────

def test_format_tiandi_groups_emits_group_members_and_two_zodiac_slot():
    assert format_tiandi_groups(("天肖",), None) == {
        "content": "天肖|兔,马,猴,猪,牛,龙",
        "xiao": "兔,马",
    }
    assert format_tiandi_groups(("地肖",), None) == {
        "content": "地肖|鼠,虎,蛇,羊,鸡,狗",
        "xiao": "鼠,虎",
    }


def test_two_zodiac_slot_is_always_a_subset_of_the_group():
    """`xiao` 必须 ⊆ 所选分组：否则「分组或两肖」与「仅分组」两个口径会互相矛盾。"""
    for label in TIANDI_LABELS:
        groups = format_tiandi_groups((label,), None)
        members = TIANDI_LABEL_FALLBACK[label]
        picked = tuple(groups["xiao"].split(","))
        assert len(picked) == TIANDI_XIAO_WIDTH
        assert all(zodiac in members for zodiac in picked), (label, picked)


def test_format_tiandi_groups_is_stable_regardless_of_history():
    """同样入参必须得到同样结果（旧实现按历史出现次数挑分组，是频率锁死的根源）。"""
    first = format_tiandi_groups(("地肖",), None)
    for _ in range(5):
        assert format_tiandi_groups(("地肖",), None) == first


def test_mode5_is_not_marked_as_three_period_display_unique():
    """只有两个分组，不可能满足「相邻三期展示值不同」，不得被登记进该约束。"""
    from prediction_generation.diversity import THREE_PERIOD_UNIQUE_MODE_IDS

    assert 5 not in THREE_PERIOD_UNIQUE_MODE_IDS
