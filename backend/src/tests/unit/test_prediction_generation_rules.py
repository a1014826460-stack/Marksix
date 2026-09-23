from __future__ import annotations

from domains.prediction.generation_rules import get_generation_rule
from domains.prediction.models import DrawTruth
from predict.mechanisms import PREDICTION_CONFIGS


def _truth() -> DrawTruth:
    return DrawTruth(
        ("01", "02", "03", "04", "05", "06", "27"),
        "27",
        "虎",
        "绿波",
        # 平特口径使用开奖 7 个号码的全部生肖：蛇/龙/兔/牛/鼠 只出现在平码里。
        ("蛇", "龙", "兔", "虎", "牛", "鼠", "虎"),
        # 平特尾口径使用开奖 7 个号码的全部尾数：1/2/3/4/5/6/7 尾。
        ("1尾", "2尾", "3尾", "4尾", "5尾", "6尾", "7尾"),
    )


def test_flat_three_xiao_hits_any_drawn_zodiac():
    """平特3肖（mode 470）按平特口径判定。"""
    config = PREDICTION_CONFIGS["pt3xiao"]
    rule = get_generation_rule(config)

    assert rule.supported is True
    assert rule.rule_id == "zodiac_flat"
    assert rule.cross_site_prefix_width == 1
    assert rule.verify_hit(config, ("鼠", "虎", "羊"), _truth(), conn=None) is True
    # 蛇只在平码里出现，平特口径下依然算命中。
    assert rule.verify_hit(config, ("蛇", "猪", "羊"), _truth(), conn=None) is True
    assert rule.verify_hit(config, ("马", "猪", "羊"), _truth(), conn=None) is False
    assert rule.signature(("鼠", "猪", "羊")) == ("鼠", "猪", "羊")
    assert rule.prefix_signature(("鼠", "猪", "羊")) == ("鼠",)


def test_head_rule_uses_special_head_instead_of_generic_zodiac_or_number_outcome():
    config = PREDICTION_CONFIGS["3tou"]
    rule = get_generation_rule(config)

    assert rule.verify_hit(config, ("2头", "3头", "4头"), _truth(), conn=None) is True
    assert rule.verify_hit(config, ("0头", "1头", "3头"), _truth(), conn=None) is False


def test_exclusion_rule_hits_only_when_special_zodiac_is_absent():
    config = PREDICTION_CONFIGS["juesha1xiao"]
    rule = get_generation_rule(config)

    assert rule.verify_hit(config, ("鼠",), _truth(), conn=None) is True
    assert rule.verify_hit(config, ("虎",), _truth(), conn=None) is False


def test_unknown_dynamic_config_is_blocked_from_future_control():
    config = type("DynamicConfig", (), {"key": "title_9999", "default_modes_id": 9999})()

    rule = get_generation_rule(config)

    assert rule.supported is False
    assert rule.block_reason == "missing_verified_rule"


def test_number_tail_size_and_half_wave_rules_use_their_own_truth_outcomes():
    number = get_generation_rule(PREDICTION_CONFIGS["ma24"])
    tail = get_generation_rule(PREDICTION_CONFIGS["pt1wei"])
    size = get_generation_rule(PREDICTION_CONFIGS["daxiao"])
    half_wave = get_generation_rule(PREDICTION_CONFIGS["jueshabanbo"])

    assert number.verify_hit(PREDICTION_CONFIGS["ma24"], ("27",), _truth(), conn=None) is True
    # 平特1尾（mode 54）按平特尾口径：开奖 7 个号码的任一尾命中即算命中。
    assert tail.rule_id == "tail_flat"
    assert tail.verify_hit(PREDICTION_CONFIGS["pt1wei"], ("7尾",), _truth(), conn=None) is True
    assert tail.verify_hit(PREDICTION_CONFIGS["pt1wei"], ("3尾",), _truth(), conn=None) is True
    assert tail.verify_hit(PREDICTION_CONFIGS["pt1wei"], ("9尾",), _truth(), conn=None) is False
    assert PREDICTION_CONFIGS["pt1wei"].flat_tail is True
    assert size.verify_hit(PREDICTION_CONFIGS["daxiao"], ("大",), _truth(), conn=None) is True
    assert half_wave.verify_hit(PREDICTION_CONFIGS["jueshabanbo"], ("绿单",), _truth(), conn=None) is False
    assert half_wave.verify_hit(PREDICTION_CONFIGS["jueshabanbo"], ("红单",), _truth(), conn=None) is True


def test_flat_two_wei_and_three_xiao_rules_cover_modes_173_and_43():
    """平特1尾2码（173）与平特2肖（43）同样按平特口径。"""
    dynamic_wei = type("DynamicConfig", (), {"key": "title_173", "default_modes_id": 173})()
    assert get_generation_rule(dynamic_wei).rule_id == "tail_flat"
    assert get_generation_rule(PREDICTION_CONFIGS["pt2xiao"]).rule_id == "zodiac_flat"
    assert PREDICTION_CONFIGS["pt2xiao"].flat_zodiac is True


def test_special_mode_108_is_blocked_until_its_row_builder_uses_controlled_candidates():
    rule = get_generation_rule(PREDICTION_CONFIGS["dxztt1"])

    assert rule.supported is False
    assert rule.block_reason == "missing_verified_rule"


def test_flat_one_xiao_rules_hit_any_drawn_zodiac_not_only_the_special():
    """平特一肖（56）与三期平特1肖（103）都按平特口径判定。"""
    from dataclasses import replace

    flat_config = replace(PREDICTION_CONFIGS["pt1xiao"], key="title_103", default_modes_id=103)
    rule = get_generation_rule(flat_config)

    assert rule.supported is True
    assert rule.rule_id == "zodiac_flat"
    assert rule.cross_site_prefix_width == 1
    # 蛇只出现在平码里（不是特码生肖“虎”），平特口径下依然算命中。
    assert rule.verify_hit(flat_config, ("蛇",), _truth(), conn=None) is True
    assert rule.verify_hit(flat_config, ("虎",), _truth(), conn=None) is True
    assert rule.verify_hit(flat_config, ("马",), _truth(), conn=None) is False
    # 平特一肖（56）使用同一条规则。
    assert get_generation_rule(PREDICTION_CONFIGS["pt1xiao"]).rule_id == rule.rule_id
    assert PREDICTION_CONFIGS["pt1xiao"].flat_zodiac is True


def test_non_flat_zodiac_rule_still_uses_the_special_zodiac():
    """三肖中特等非平特玩法仍按特码生肖判定。"""
    config = PREDICTION_CONFIGS["3zxt"]
    rule = get_generation_rule(config)

    assert rule.rule_id == "zodiac"
    assert rule.verify_hit(config, ("蛇",), _truth(), conn=None) is False
    assert rule.verify_hit(config, ("虎",), _truth(), conn=None) is True
    assert config.flat_zodiac is False


def test_image_and_text_modes_are_blocked_until_their_content_can_be_verified():
    for key in ("sxztu", "brainteaser", "pmtj_image", "tw_pmt_image", "yijuzhenyan"):
        rule = get_generation_rule(PREDICTION_CONFIGS[key])

        assert rule.supported is False
        assert rule.block_reason == "missing_verified_rule"
