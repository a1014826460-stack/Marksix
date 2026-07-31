from __future__ import annotations

from vendor import homepage_modules
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


def test_wuxiao_wuma_uses_explicit_zodiac_and_code_fallback_when_mode151_is_empty(monkeypatch):
    rows_by_mode = {
        47: [{"year": "2026", "term": "180", "content": "鼠牛虎兔", "res_code": "04", "res_sx": "兔", "status": 1}],
        69: [{"year": "2026", "term": "180", "content": "鼠牛虎", "res_code": "04", "res_sx": "兔", "status": 1}],
        151: [],
        49: [{"year": "2026", "term": "180", "content": "鼠牛虎兔龙蛇羊", "res_code": "04", "res_sx": "兔", "status": 1}],
        34: [{"year": "2026", "term": "180", "content": "01,02,03,04,05,06", "res_code": "04", "res_sx": "兔", "status": 1}],
    }
    monkeypatch.setattr(
        homepage_modules,
        "_load_mode_rows",
        lambda _db, **kwargs: rows_by_mode[kwargs["modes_id"]],
    )

    module = homepage_modules._build_wuxiao_wuma(
        homepage_modules.VendorModuleContext(site={}, lottery_type=3, web_id=11, history_limit=1),
        "unused",
    )

    assert module["history"][0]["groups"]["xiao_5"] == ["鼠", "牛", "虎", "兔", "龙"]
    assert module["history"][0]["groups"]["code_5"] == ["01", "02", "03", "04", "05"]


def test_wuxiao_wuma_fallback_skips_issues_without_both_required_fields(monkeypatch):
    rows_by_mode = {
        47: [],
        69: [],
        151: [],
        49: [
            {"year": "2026", "term": "181", "content": "鼠牛虎兔龙", "status": 0},
            {"year": "2026", "term": "180", "content": "鼠牛虎兔龙", "res_code": "04", "res_sx": "兔", "status": 1},
        ],
        34: [
            {"year": "2026", "term": "180", "content": "01,02,03,04,05", "res_code": "04", "res_sx": "兔", "status": 1},
        ],
    }
    monkeypatch.setattr(
        homepage_modules,
        "_load_mode_rows",
        lambda _db, **kwargs: rows_by_mode[kwargs["modes_id"]][: kwargs["limit"]],
    )

    module = homepage_modules._build_wuxiao_wuma(
        homepage_modules.VendorModuleContext(site={}, lottery_type=3, web_id=11, history_limit=1),
        "unused",
    )

    assert [row["issue"] for row in module["history"]] == ["2026180"]
    assert module["history"][0]["groups"]["code_5"] == ["01", "02", "03", "04", "05"]
