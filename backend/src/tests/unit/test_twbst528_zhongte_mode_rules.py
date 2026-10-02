from __future__ import annotations

"""twbst528 三块中特面板的权威 mode（155 / 133 / 117）的生成规则与正文口径。

背景（2026-10-01）：【吉美丑凶】/【前后中特】/【③肖防③码】过去借 `pt3xiao`（平特3肖）与
`qianhou_texiao`（前后特肖，只比 2 肖）的行，判定口径与面板展示不一致。改绑各自的权威 mode 后：

- mode 155「吉美凶丑（2选1，全肖）」/ mode 133「前后生肖」：候选是**分组名**，
  真实目标必须由「特肖 → 所属分组」映射得到，否则每期都会被判成不中；
- mode 117「3肖4码」：候选是 3 个生肖，沿用通用 `zodiac` 规则（`contains_hit`）。

本文件把这几条口径钉在测试里：规则登记、真实目标换算、正文 formatter、分组映射。
"""

from domains.prediction.generation_rules import RULE_BY_MODE_ID, get_generation_rule
from domains.prediction.models import DrawTruth
from predict.mechanisms import PREDICTION_CONFIGS


def _truth(special_zodiac: str) -> DrawTruth:
    return DrawTruth(
        ("01", "02", "03", "04", "05", "06", "07"),
        "07",
        special_zodiac,
        "红波",
        (special_zodiac,) * 7,
        ("1尾", "2尾", "3尾", "4尾", "5尾", "6尾", "7尾"),
    )


def test_registered_rules_for_the_three_panels():
    assert RULE_BY_MODE_ID[117].rule_id == "zodiac"
    assert RULE_BY_MODE_ID[155].rule_id == "zodiac_group"
    assert RULE_BY_MODE_ID[133].rule_id == "zodiac_group"
    for mode_id in (117, 155, 133):
        assert RULE_BY_MODE_ID[mode_id].supported is True
        assert RULE_BY_MODE_ID[mode_id].cross_site_prefix_width == 1


def test_jimei_xiongchou_truth_outcome_is_the_group_label():
    """特肖 → 分组名，而不是特肖本身：候选是「吉美肖 / 凶丑肖」。"""
    config = PREDICTION_CONFIGS["jimei_xiongchou"]
    rule = get_generation_rule(config)

    assert rule.verify_hit(config, ("吉美肖",), _truth("羊"), conn=None) is True
    assert rule.verify_hit(config, ("凶丑肖",), _truth("羊"), conn=None) is False
    assert rule.verify_hit(config, ("凶丑肖",), _truth("猴"), conn=None) is True
    assert rule.verify_hit(config, ("吉美肖",), _truth("猴"), conn=None) is False
    # 特肖缺失时无法判定，必须返回 False（不能默认命中）
    assert rule.truth_outcome(_truth(""), None) == ""
    assert rule.verify_hit(config, ("吉美肖",), _truth(""), conn=None) is False


def test_qianhou_shengxiao_truth_outcome_is_the_group_label():
    """特肖 → 「前肖 / 后肖」；与 mode 219「前后特肖」的 2 肖候选区分开。"""
    config = PREDICTION_CONFIGS["qianhou_shengxiao"]
    rule = get_generation_rule(config)

    assert rule.verify_hit(config, ("前肖",), _truth("鼠"), conn=None) is True
    assert rule.verify_hit(config, ("后肖",), _truth("鼠"), conn=None) is False
    assert rule.verify_hit(config, ("后肖",), _truth("羊"), conn=None) is True
    assert rule.verify_hit(config, ("前肖",), _truth("羊"), conn=None) is False


def test_sanxiao_siwei_xiao_keeps_the_plain_zodiac_rule():
    """mode 117 的候选是 3 个生肖，规则沿用 `zodiac`（码组半区不属于本 mode）。"""
    config = PREDICTION_CONFIGS["sanxiao_siwei_xiao"]
    rule = get_generation_rule(config)

    assert config.default_modes_id == 117
    assert config.label_count == 3
    assert rule.verify_hit(config, ("虎", "马", "狗"), _truth("马"), conn=None) is True
    assert rule.verify_hit(config, ("虎", "马", "狗"), _truth("羊"), conn=None) is False


def test_group_formatters_emit_label_and_members():
    """正文形态 `分组名|成员生肖`，与厂商 `mode_payload_155/133` 完全一致。"""
    from predict.mechanisms import (
        JIMEI_LABEL_FALLBACK,
        QIANHOU_LABEL_FALLBACK,
        format_group_member_groups,
    )

    assert format_group_member_groups(("凶丑肖",), {}, JIMEI_LABEL_FALLBACK) == [
        "凶丑肖|鼠,牛,虎,猴,狗,猪"
    ]
    assert format_group_member_groups(("吉美肖",), {}, JIMEI_LABEL_FALLBACK) == [
        "吉美肖|兔,龙,蛇,马,羊,鸡"
    ]
    assert format_group_member_groups(("后肖",), {}, QIANHOU_LABEL_FALLBACK) == [
        "后肖|马,羊,猴,鸡,狗,猪"
    ]
    assert format_group_member_groups(("前肖",), {}, QIANHOU_LABEL_FALLBACK) == [
        "前肖|鼠,牛,虎,兔,龙,蛇"
    ]
