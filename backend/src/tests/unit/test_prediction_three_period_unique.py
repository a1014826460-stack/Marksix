"""相邻连续三期的展示值不得相同。

覆盖用户指定修复的五个模块：28 / 57 / 62 / 63 / 108。
这里的“展示值”按各模块前台实际渲染的第一个槽位定义：
  - 28 / 57 / 63 / 108：content 数组首项 `标签|号码` 的标签部分（或 content 首字段）
  - 62：title（欲钱解特诗，前台直接渲染 title）
"""

from __future__ import annotations

import json

from prediction_generation import diversity


# ---------- 展示值提取 ----------


def test_display_token_for_pipe_label_content():
    row = {"content": '["家禽|牛,马,羊,鸡,狗,猪"]'}
    assert diversity.display_token_for_row(63, row) == "家禽"


def test_display_token_for_single_field_content():
    row = {"content": '["大|25,26,27"]'}
    assert diversity.display_token_for_row(57, row) == "大"


def test_display_token_for_text_mode_uses_title():
    row = {"title": "欲钱解特诗", "content": ""}
    assert diversity.display_token_for_row(62, row) == "欲钱解特诗"


def test_display_token_ignores_non_scoped_mode():
    row = {"content": '["家禽|牛,马,羊,鸡,狗,猪"]'}
    assert diversity.display_token_for_row(46, row) is None


def test_display_token_handles_missing_content():
    assert diversity.display_token_for_row(63, {}) is None


# ---------- 候选取值枚举 ----------


def test_distinct_tokens_returns_all_pipe_labels():
    content = '["家禽|牛,马,羊,鸡,狗,猪"]'
    assert diversity.distinct_tokens_for_content(content) == ("家禽",)


def test_distinct_tokens_returns_both_size_labels():
    content = '["大|25,26", "小|01,02"]'
    assert diversity.distinct_tokens_for_content(content) == ("大", "小")


# ---------- 三期不同规则 ----------


def test_repeated_token_is_replaced_after_two_identical_periods():
    """前两期都是“家禽”，第三期不得再是“家禽”。"""
    row = {"content": '["家禽|牛,马,羊,鸡,狗,猪"]'}
    result = diversity.enforce_three_period_uniqueness(
        mode_id=63,
        row_data=row,
        recent_rows=[
            {"content": '["家禽|牛,马,羊,鸡,狗,猪"]'},
            {"content": '["家禽|牛,马,羊,鸡,狗,猪"]'},
        ],
        alternative_content_templates=['["野兽|鼠,虎,兔,龙,蛇,猴"]'],
    )
    assert diversity.display_token_for_row(63, result) == "野兽"
    assert json.loads(result["content"]) == ["野兽|鼠,虎,兔,龙,蛇,猴"]


def test_repeated_token_keeps_row_when_previous_period_differs():
    """只有上一期相同、上上期不同，则不构成连续三期，保持原值。"""
    row = {"content": '["家禽|牛,马,羊,鸡,狗,猪"]'}
    result = diversity.enforce_three_period_uniqueness(
        mode_id=63,
        row_data=row,
        recent_rows=[
            {"content": '["家禽|牛,马,羊,鸡,狗,猪"]'},
            {"content": '["野兽|鼠,虎,兔,龙,蛇,猴"]'},
        ],
        alternative_content_templates=['["野兽|鼠,虎,兔,龙,蛇,猴"]'],
    )
    assert diversity.display_token_for_row(63, result) == "家禽"


def test_no_repair_without_two_identical_preceding_periods():
    row = {"content": '["大|25,26"]'}
    result = diversity.enforce_three_period_uniqueness(
        mode_id=57,
        row_data=row,
        recent_rows=[{"content": '["小|01,02"]'}],
        alternative_content_templates=['["小|01,02"]'],
    )
    assert diversity.display_token_for_row(57, result) == "大"


def test_alternatives_are_rotated_over_consecutive_terms():
    """连续生成时必须每期都换一个不同取值，而不是来回抖动。"""
    recent = [
        {"content": '["家禽|牛,马,羊,鸡,狗,猪"]'},
        {"content": '["野兽|鼠,虎,兔,龙,蛇,猴"]'},
    ]
    tokens = []
    for _ in range(4):
        row = {"content": '["家禽|牛,马,羊,鸡,狗,猪"]'}
        row = diversity.enforce_three_period_uniqueness(
            mode_id=63,
            row_data=row,
            recent_rows=recent,
            alternative_content_templates=['["野兽|鼠,虎,兔,龙,蛇,猴"]'],
        )
        token = diversity.display_token_for_row(63, row)
        tokens.append(token)
        recent.insert(0, {"content": row["content"]})

    for index in range(len(tokens) - 2):
        window = tokens[index:index + 3]
        assert len(set(window)) > 1, f"连续三期相同: {window}"


def test_two_item_content_does_not_toggle_same_value_forever():
    """mode 28：前两期首标签分别是“单”“单”时，第三期必须是“双”。"""
    row = {"content": '["单|01,03", "双|02,04"]'}
    result = diversity.enforce_three_period_uniqueness(
        mode_id=28,
        row_data=row,
        recent_rows=[
            {"content": '["单|01,03", "双|02,04"]'},
            {"content": '["单|01,03", "双|02,04"]'},
        ],
    )
    assert diversity.display_token_for_row(28, result) == "双"
    assert json.loads(result["content"]) == ["双|02,04", "单|01,03"]


def test_size_mode_single_item_can_be_switched():
    row = {"content": '["小|01,02,03"]'}
    result = diversity.enforce_three_period_uniqueness(
        mode_id=108,
        row_data=row,
        recent_rows=[
            {"content": '["小|01,02,03"]'},
            {"content": '["小|01,02,03"]'},
        ],
        alternative_content_templates=['["大|25,26,27"]'],
    )
    assert diversity.display_token_for_row(108, result) == "大"
    assert json.loads(result["content"]) == ["大|25,26,27"]


def test_no_alternative_available_marks_diversity_warning():
    row = {"content": '["家禽|牛,马,羊,鸡,狗,猪"]'}
    result = diversity.enforce_three_period_uniqueness(
        mode_id=63,
        row_data=row,
        recent_rows=[
            {"content": '["家禽|牛,马,羊,鸡,狗,猪"]'},
            {"content": '["家禽|牛,马,羊,鸡,狗,猪"]'},
        ],
        alternative_content_templates=[],
    )
    assert diversity.display_token_for_row(63, result) == "家禽"
    assert "mode_id=63" in str(result.get("_diversity_warning", ""))


def test_text_mode_uses_alternative_title():
    row = {"title": "欲钱解特诗", "content": ""}
    result = diversity.enforce_three_period_uniqueness(
        mode_id=62,
        row_data=row,
        recent_rows=[
            {"title": "欲钱解特诗", "content": ""},
            {"title": "欲钱解特诗", "content": ""},
        ],
        alternative_text_payloads=[
            {"title": "守株待兔", "content": "", "jiexi": ""},
            {"title": "欲钱解特诗", "content": "", "jiexi": ""},
        ],
    )
    assert result["title"] == "守株待兔"


def test_placeholder_replaced_by_real_candidate():
    """占位文案不是真实诗句：有真实候选时直接替换。"""
    row = {"title": "欲钱解特诗", "content": ""}
    result = diversity.replace_text_placeholder(
        62,
        row,
        alternative_text_payloads=[
            {"title": "欲钱解特诗", "content": ""},
            {"title": "竹影横斜三径晚,篱边菊蕊九秋香", "content": ""},
        ],
    )
    assert result["title"] == "竹影横斜三径晚,篱边菊蕊九秋香"


def test_real_title_is_not_touched_by_placeholder_replacement():
    row = {"title": "暮云低锁千山静,归鸟知还九曲回", "content": ""}
    result = diversity.replace_text_placeholder(
        62, row, alternative_text_payloads=[{"title": "别的诗句", "content": ""}]
    )
    assert result["title"] == row["title"]


def test_placeholder_kept_when_no_real_candidate():
    row = {"title": "欲钱解特诗", "content": ""}
    result = diversity.replace_text_placeholder(
        62, row, alternative_text_payloads=[{"title": "欲钱解特诗", "content": ""}]
    )
    assert result["title"] == "欲钱解特诗"


def test_unscoped_mode_is_left_untouched():
    row = {"content": '["家禽|牛,马,羊,鸡,狗,猪"]'}
    result = diversity.enforce_three_period_uniqueness(
        mode_id=46,
        row_data=row,
        recent_rows=[
            {"content": '["家禽|牛,马,羊,鸡,狗,猪"]'},
            {"content": '["家禽|牛,马,羊,鸡,狗,猪"]'},
        ],
        alternative_content_templates=['["野兽|鼠,虎,兔,龙,蛇,猴"]'],
    )
    assert result == row


# ---------- content 形状归一 ----------


def test_template_json_array_is_rewritten_as_json_array():
    row = {"content": '["家禽|牛,马,羊,鸡,狗,猪"]'}
    result = diversity.enforce_three_period_uniqueness(
        mode_id=63,
        row_data=row,
        recent_rows=[
            {"content": '["家禽|牛,马,羊,鸡,狗,猪"]'},
            {"content": '["家禽|牛,马,羊,鸡,狗,猪"]'},
        ],
        alternative_content_templates=['["野兽|鼠,虎,兔,龙,蛇,猴"]'],
    )
    assert json.loads(result["content"]) == ["野兽|鼠,虎,兔,龙,蛇,猴"]


def test_template_plain_string_is_rewritten_as_plain_string():
    """mode 28/57/108 的 formatter 返回普通字符串，回写也必须保持普通字符串。"""
    row = {"content": "单|01,03,05"}
    result = diversity.enforce_three_period_uniqueness(
        mode_id=28,
        row_data=row,
        recent_rows=[
            {"content": "单|01,03,05"},
            {"content": "单|01,03,05"},
        ],
        alternative_content_templates=["双|02,04,06"],
    )
    assert result["content"] == "双|02,04,06"
    assert diversity.display_token_for_row(28, result) == "双"


def test_plain_label_template_builds_pipe_item():
    """模板只有标签（无号码）时，也应生成合法的 `标签|号码` 项。"""
    row = {"content": '["大|25,26"]'}
    result = diversity.enforce_three_period_uniqueness(
        mode_id=108,
        row_data=row,
        recent_rows=[
            {"content": '["大|25,26"]'},
            {"content": '["大|25,26"]'},
        ],
        alternative_content_templates=["小"],
    )
    assert diversity.display_token_for_row(108, result) == "小"
