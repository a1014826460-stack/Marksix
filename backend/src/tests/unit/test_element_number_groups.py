"""号码五行必须按 fixed_data 的**号码分组**判定，不能用生肖五行或过期硬编码表。

回归背景（2026-09-29，用户报障）：
`public/api.py` 曾维护一份过期的硬编码五行表（37 → 火），而 `public.fixed_data` /
`mode_payload_53` 的号码分组是 37 → 号码五行。结果 270 期「精准五行」预测 `金+土+木`、
开奖特码 37（马）时：按生肖看马是火肖，按号码看 37 属号码五行 —— 旧实现取到「火」，
判定为「错」；正确口径应取号码五行，落在预测三行内 → 「对」。

2026-09-29 二次改判：号码五行整体切到用户给出的**新表**（相对上一版 25 个号码换组，
规律 new(x)=old(x-1)，01 归水），`public.fixed_data` / `created.mode_payload_53` / `_482`
由 versioned migration 32 同步重刷。本文件的期望值一律按**新表**重算。
"""

from __future__ import annotations

from predict.common import (
    ELEMENT_NUMBER_GROUPS,
    ELEMENT_ORDER,
    TIANDI_ZODIACS,
    build_element_number_map,
    canonical_element_number_map,
)
from public import api


def test_number_groups_cover_all_49_without_overlap():
    seen: dict[str, str] = {}
    for element in ELEMENT_ORDER:
        assert element in ELEMENT_NUMBER_GROUPS, f"缺少五行分组 {element}"
        for number in ELEMENT_NUMBER_GROUPS[element]:
            assert number not in seen, f"{number} 同时属于 {seen[number]} 和 {element}"
            seen[number] = element
    assert sorted(seen) == [f"{index:02d}" for index in range(1, 50)]


def test_element_groups_match_fixed_data_samples():
    # 与 public.fixed_data sign='五行' / mode_payload_53 正文一致（用户给出的新表）。
    assert ELEMENT_NUMBER_GROUPS["木"] == ("08", "09", "16", "17", "24", "25", "38", "39", "46", "47")
    assert "37" in ELEMENT_NUMBER_GROUPS["土"]
    assert "49" in ELEMENT_NUMBER_GROUPS["火"]


def test_special_number_element_is_number_based_not_zodiac_based():
    mapping = canonical_element_number_map()
    # 37 的生肖是马（火肖），但号码五行是土；马（火肖）的号码 01/13/25/37/49
    # 在新表里分属 水/金/木/土/火 —— 一律不能用生肖五行替代号码五行。
    assert mapping["37"] == "土"
    assert mapping["04"] == "金"
    assert mapping["49"] == "火"
    assert mapping["22"] == "水"


def test_public_api_uses_the_canonical_map():
    assert api._ELEMENT_MAP == canonical_element_number_map()
    assert len(api._ELEMENT_MAP) == 49


def test_build_element_number_map_does_not_need_the_database():
    assert build_element_number_map(None) == canonical_element_number_map()


def test_composite_outcome_carries_the_number_element():
    row = {
        "res_code": "01,02,03,04,05,06,37",
        "res_sx": "鼠,牛,虎,兔,龙,蛇,马",
        "res_color": "red,red,red,red,red,red,green",
    }
    atoms = api._compute_outcome_from_row(row).split("|")
    assert "土" in atoms, "37 的五行原子应为土"
    assert "火" not in atoms, "不得用马的火肖替代号码五行"


def test_tiandi_groups_match_site_tables():
    assert TIANDI_ZODIACS["天肖"] == ("兔", "马", "猴", "猪", "牛", "龙")
    assert TIANDI_ZODIACS["地肖"] == ("鼠", "虎", "蛇", "羊", "鸡", "狗")


def test_domestic_wild_prediction_category_comes_from_the_prediction_text():
    """预测分类取正文（预测），不取按特别生肖推导的开奖分类 —— 否则卡片恒为「准」。"""
    assert api.domestic_wild_prediction_category({"content": '["家禽|牛,狗,猪,羊,马,鸡"]'}) == "家禽"
    assert api.domestic_wild_prediction_category({"content": '["野兽|兔,猴,虎,蛇,鼠,龙"]'}) == "野兽"
    assert api.domestic_wild_prediction_category({"content": "家禽|牛,马"}) == "家禽"
    assert api.domestic_wild_prediction_category({"content": '["家禽"]'}) == "家禽"
    assert api.domestic_wild_prediction_category({"content": ""}) == ""
    assert api.domestic_wild_prediction_category({"content": "暂无后端资料"}) == ""


def test_annotation_exposes_both_result_and_prediction_category():
    rows = [
        # 预测「野兽」，开奖特肖 马 → 开奖分类是家禽：两者必须都能拿到，展示用预测值。
        {"res_code": "01,02,37", "res_sx": "鼠,牛,马", "content": '["野兽|兔,猴,虎,蛇,鼠,龙"]'},
        {"res_code": "", "res_sx": "", "content": "家禽|牛,马"},
    ]
    annotated = api.attach_domestic_wild_result_category(rows, {"马": "家禽", "牛": "家禽"})

    assert annotated[0]["domestic_wild_category"] == "家禽"
    assert annotated[0]["domestic_wild_prediction_category"] == "野兽"
    assert annotated[1]["domestic_wild_prediction_category"] == "家禽"
    assert "domestic_wild_category" not in annotated[1]  # 未开奖没有开奖分类
