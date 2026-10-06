"""`parse_zodiac_chars` 必须同时认简体「龙」与繁体「龍」。

背景（2026-10-02 线上报障）
--------------------------
twbst528 首页【一句中平特】2026278 期显示 `丈夫解男肖，龙虎鼠猴牛马狗。 开:03龙错`，
twcaibawang【一句真言】同期 `真言解肖主前：羊虎龙兔牛猴蛇 開:龙03` 整块不标黄 ——
两站的候选里都写着「龙」，开奖特肖也正是「龙」，却判成未命中。

根因：`predict/categories/content_columns.py::parse_zodiac_chars` 的字符类是
`[鼠牛虎兔龍蛇马馬羊猴鸡雞狗猪豬]` —— 它列了繁体「龍」却**漏了简体「龙」**
（`predict.common.parse_zodiac_content` 用的是 `[鼠牛虎兔龍龙…]`，两种都收）。
mode 50「一句真言」/ mode 52「四字玄机」等玩法的候选都由这个解析器从 `jiexi` 抽取，
于是候选集合里少了「龙」：`contains_hit` 的 `any(label in outcome)` 遍历不到「龙」，
「开奖特肖 = 龙」的期一律判「错」。

修法：字符类收敛成唯一来源 `predict.common.ZODIAC_CHAR_CLASS`（简体 + 繁体齐全），
`content_columns.parse_zodiac_chars` 与 `common.parse_zodiac_content` 共用。

本文件锁定：① 两种写法都能抽出「龙」；② 12 生肖简体串一个不漏（守住整类缺陷）；
③ 走真实机制配置复算 mode 50 的 `is_correct`（线上报障样例）。
"""
from __future__ import annotations

from predict.categories import content_columns
from predict.common import (
    ZODIAC_CHAR_CLASS,
    ZODIAC_ORDER,
    normalize_zodiac_member,
    parse_zodiac_content,
    zodiac_category_labels,
)
from predict.mechanisms import get_prediction_config
from public.api import _check_correct_by_mechanism, serialize_public_history_row

#: 线上报障样例：twbst528 的 `jiexi`（web 10）与 twcaibawang 的 `jiexi`（web 5）。
TWST528_JIEXI = "龙虎鼠猴牛马狗"
TWCAIBAWANG_JIEXI = "羊虎龙兔牛猴蛇"


def test_simplified_and_traditional_long_are_both_parsed():
    assert content_columns.parse_zodiac_chars("羊虎龙兔牛猴蛇") == ("羊", "虎", "龙", "兔", "牛", "猴", "蛇")
    assert content_columns.parse_zodiac_chars("羊虎龍兔牛猴蛇") == ("羊", "虎", "龙", "兔", "牛", "猴", "蛇")
    # 两种写法混写时只留一个「龙」（顺序去重）。
    assert content_columns.parse_zodiac_chars("龙虎龍鼠") == ("龙", "虎", "鼠")


def test_all_twelve_simplified_zodiacs_are_parsed():
    """简体 12 生肖一个不漏（早期字符类整类漏「龙」）。"""
    text = "".join(ZODIAC_ORDER)
    assert content_columns.parse_zodiac_chars(text) == tuple(ZODIAC_ORDER)
    # 繁体写法归一化到简体后同样是 12 个。
    traditional = text.replace("龙", "龍").replace("马", "馬").replace("鸡", "雞").replace("猪", "豬")
    assert content_columns.parse_zodiac_chars(traditional) == tuple(ZODIAC_ORDER)


def test_zodiac_char_class_is_the_single_source_for_both_parsers():
    """两个解析器共用同一份字符类：`龍龙` 必须都在里面。"""
    assert "龍" in ZODIAC_CHAR_CLASS and "龙" in ZODIAC_CHAR_CLASS
    assert set(content_columns.parse_zodiac_chars("龍龙")) == {"龙"}
    assert set(parse_zodiac_content("龍,龙")) == {"龙"}


def _opened_row(jiexi: str) -> dict[str, object]:
    """一行 mode 50 的 payload：2026-278 期真值（03 龙）。"""
    return {
        "id": "regression",
        "web": "10",
        "type": "3",
        "year": "2026",
        "term": "278",
        "res_code": "06,47,45,01,41,37,03",
        "res_sx": "牛,猴,狗,马,虎,马,龙",
        "res_color": "red,red,blue,blue,blue,green,green",
        "title": "敢笑黄巢不丈夫",
        "content": "丈夫解男肖，龙虎鼠猴牛马狗。",
        "jiexi": jiexi,
        "draw_is_opened": True,
    }


def test_mode50_row_whose_only_candidate_is_long_is_a_hit():
    config = get_prediction_config("yijuzhenyan")
    for jiexi in (TWST528_JIEXI, TWCAIBAWANG_JIEXI):
        row = _opened_row(jiexi)
        assert "龙" in content_columns.parse_zodiac_chars(jiexi)
        assert _check_correct_by_mechanism(jiexi, row, config) is True
        serialized = serialize_public_history_row(row, config)
        assert serialized["result_text"] == "龙03"
        assert serialized["is_correct"] is True


def test_mode50_row_without_long_is_still_a_miss():
    """回归护栏：没有「龙」的行仍按未命中判（不得为了修「龙」把判定放宽）。"""
    config = get_prediction_config("yijuzhenyan")
    row = _opened_row("羊虎兔牛猴蛇鼠")
    assert _check_correct_by_mechanism("羊虎兔牛猴蛇鼠", row, config) is False
    assert serialize_public_history_row(row, config)["is_correct"] is False


# ── 同族缺陷（2026-10-03 十站扫描）：分组里的生肖**错别字「免」** ────────────────
# `public.fixed_data`（文武肖 id 262）与 `mode_payload_144/179` 的正文把「兔」写成「免」
# （实测 174 行），于是「特肖 = 兔」时该行拿不到任何分类标签 → 文肖/武肖恒判「错」。
# 与繁简归一不同，这个替换**只对分组里的单字成员**生效：自由文本里的「免」是正常用词
# （mode 59 幽默正文「不免得意的问」），不能整段替换。

WENWU_CONTENT = '["文肖|鼠,免,龙,羊,鸡,猪"]'


def test_member_typo_mian_is_treated_as_tu():
    assert normalize_zodiac_member("免") == "兔"
    assert normalize_zodiac_member("龍") == "龙"
    assert normalize_zodiac_member("兔") == "兔"
    assert zodiac_category_labels(WENWU_CONTENT, "兔") == ("文肖",)
    # 武肖组成员不受影响；写简体「兔」的历史行结果一致。
    assert zodiac_category_labels(WENWU_CONTENT, "马") == ()
    assert zodiac_category_labels('["文肖|鼠,兔,龙,羊,鸡,猪"]', "兔") == ("文肖",)


def test_member_typo_does_not_touch_free_text():
    """自由文本（非分组）里的「免」不得被替换成「兔」。"""
    humor = '["独家幽默：商场门口遇到了初中同学，不免得意的问他"]'
    assert zodiac_category_labels(humor, "兔") == ()
    # 松散文本按原样返回（没有任何「标签|成员」分组）。
    assert normalize_zodiac_member("不免得意的问") == "不免得意的问"
