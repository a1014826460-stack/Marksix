from __future__ import annotations

from predict import mechanisms


def test_content_columns_category_reexports_legacy_helpers():
    from predict.categories import content_columns

    assert mechanisms.jiexi_content_from_row is content_columns.jiexi_content_from_row
    assert mechanisms.tail_code_content_from_row is content_columns.tail_code_content_from_row
    assert mechanisms.join_columns_content_loader is content_columns.join_columns_content_loader
    assert mechanisms.parse_tail_digit_content is content_columns.parse_tail_digit_content
    assert mechanisms.parse_zodiac_chars is content_columns.parse_zodiac_chars
    assert mechanisms.parse_wave_chars is content_columns.parse_wave_chars


def test_content_columns_preserve_legacy_column_and_label_shapes():
    from predict.categories import content_columns

    row = {
        "jiexi": "鼠虎兔龙",
        "code": "1,3,5",
        "hei": "鼠,牛,虎",
        "bai": "兔,龙,蛇",
        "first": "甲",
        "second": "乙",
    }

    assert content_columns.jiexi_content_from_row(row) == "鼠虎兔龙"
    assert content_columns.tail_code_content_from_row(row) == "1,3,5"
    assert content_columns.black_white_content_from_row(row) == "鼠,牛,虎,兔,龙,蛇"
    assert content_columns.join_columns_content_loader(("first", "second"))(row) == "甲,乙"
    assert content_columns.parse_tail_digit_content('["1尾|01,11","三尾|03,13"]') == ("1尾", "3尾")
    # Preserve the legacy character parser: it recognizes the traditional 龙 form.
    assert content_columns.parse_zodiac_chars("鼠虎兔龍") == ("鼠", "虎", "兔", "龙")
    assert content_columns.parse_wave_chars("红蓝绿") == ("红波", "蓝波", "绿波")


def test_static_configs_bind_content_column_category_helpers():
    from predict.categories import content_columns

    assert mechanisms.PREDICTION_CONFIGS["yijuzhenyan"].content_loader is content_columns.jiexi_content_from_row
    assert mechanisms.PREDICTION_CONFIGS["heibai3xiao"].content_loader is content_columns.black_white_content_from_row
