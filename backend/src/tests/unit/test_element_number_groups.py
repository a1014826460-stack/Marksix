"""号码五行必须按 fixed_data 的**号码分组**判定，不能用生肖五行或过期硬编码表。

回归背景（2026-09-29，用户报障）：
`public/api.py` 曾维护一份过期的硬编码五行表（37 → 火），而 `public.fixed_data` /
`mode_payload_53` 的号码分组是 37 → 木。结果 270 期「精准五行」预测 `金+土+木`、
开奖特码 37（马）时：按生肖看马是火肖，按号码看 37 属木 —— 旧实现取到「火」，
判定为「错」；正确口径应取号码五行「木」，落在预测三行内 → 「对」。
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
    # 与 public.fixed_data sign='五行' / mode_payload_53 正文一致（用户给出的木组）。
    assert ELEMENT_NUMBER_GROUPS["木"] == ("07", "08", "15", "16", "23", "24", "37", "38", "45", "46")
    assert "37" in ELEMENT_NUMBER_GROUPS["木"]
    assert "49" in ELEMENT_NUMBER_GROUPS["土"]


def test_special_number_element_is_number_based_not_zodiac_based():
    mapping = canonical_element_number_map()
    # 37 = 龙（生肖），但号码五行是木；马（火肖）的号码 11/23/35/47 属金/木/…，
    # 一律不能用生肖五行替代号码五行。
    assert mapping["37"] == "木"
    assert mapping["04"] == "金"
    assert mapping["49"] == "土"
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
    assert "木" in atoms, "37 的五行原子应为木"
    assert "火" not in atoms, "不得用马的火肖替代号码五行"


def test_tiandi_groups_match_site_tables():
    assert TIANDI_ZODIACS["天肖"] == ("兔", "马", "猴", "猪", "牛", "龙")
    assert TIANDI_ZODIACS["地肖"] == ("鼠", "虎", "蛇", "羊", "鸡", "狗")
