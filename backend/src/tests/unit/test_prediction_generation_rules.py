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
    )


def test_mode_470_hits_when_any_of_its_three_zodiacs_matches_special_zodiac():
    config = PREDICTION_CONFIGS["pt3xiao"]
    rule = get_generation_rule(config)

    assert rule.supported is True
    assert rule.cross_site_prefix_width == 1
    assert rule.verify_hit(config, ("鼠", "虎", "羊"), _truth(), conn=None) is True
    assert rule.verify_hit(config, ("鼠", "猪", "羊"), _truth(), conn=None) is False
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
    assert tail.verify_hit(PREDICTION_CONFIGS["pt1wei"], ("7尾",), _truth(), conn=None) is True
    assert size.verify_hit(PREDICTION_CONFIGS["daxiao"], ("大",), _truth(), conn=None) is True
    assert half_wave.verify_hit(PREDICTION_CONFIGS["jueshabanbo"], ("绿单",), _truth(), conn=None) is False
    assert half_wave.verify_hit(PREDICTION_CONFIGS["jueshabanbo"], ("红单",), _truth(), conn=None) is True


def test_special_mode_108_is_blocked_until_its_row_builder_uses_controlled_candidates():
    rule = get_generation_rule(PREDICTION_CONFIGS["dxztt1"])

    assert rule.supported is False
    assert rule.block_reason == "missing_verified_rule"


def test_image_and_text_modes_are_blocked_until_their_content_can_be_verified():
    for key in ("sxztu", "brainteaser", "pmtj_image", "tw_pmt_image", "yijuzhenyan"):
        rule = get_generation_rule(PREDICTION_CONFIGS[key])

        assert rule.supported is False
        assert rule.block_reason == "missing_verified_rule"
