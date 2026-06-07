from __future__ import annotations

from vendor.homepage_modules import _parse_label_code_pairs, _split_labels


def test_parse_label_code_pairs_supports_space_separated_pseudo_json_array():
    value = '["猪|08" "猴|11" "鸡|10" "龙|03" "狗|09" "蛇|02" "牛|06" "兔|04"]'

    pairs = _parse_label_code_pairs(value)

    assert [label for label, _codes in pairs[:5]] == ["猪", "猴", "鸡", "龙", "狗"]
    assert pairs[0][1] == ["08"]
    assert pairs[1][1] == ["11"]


def test_split_labels_supports_plain_zodiac_sequence_without_commas():
    value = "猪兔鸡猴羊"

    labels = _split_labels(value)

    assert labels == ["猪", "兔", "鸡", "猴", "羊"]
