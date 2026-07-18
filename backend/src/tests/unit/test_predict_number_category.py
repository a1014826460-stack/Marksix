from __future__ import annotations

from predict import mechanisms


class FakeConn:
    def table_exists(self, table_name):
        return table_name == "fixed_data"

    def execute(self, _sql, params=()):
        sign = params[0] if params else ""
        rows = []
        if sign == "7段":
            rows = [
                {"id": 1, "name": "1段", "code": "01,02"},
                {"id": 2, "name": "2段", "code": "08,09"},
            ]

        class Cursor:
            def fetchall(self_nonlocal):
                return rows

        return Cursor()


def test_number_category_reexports_number_and_segment_helpers():
    from predict.categories import number

    assert mechanisms.special_number_from_row is number.special_number_from_row
    assert mechanisms.format_24_numbers is number.format_24_numbers
    assert mechanisms.special_segment_from_row is number.special_segment_from_row
    assert mechanisms.format_segment_groups is number.format_segment_groups
    assert mechanisms.format_split_number_columns is number.format_split_number_columns


def test_static_configs_bind_number_category_helpers():
    from predict.categories import number

    assert mechanisms.PREDICTION_CONFIGS["ma24"].content_formatter is number.format_24_numbers
    assert mechanisms.PREDICTION_CONFIGS["siduanzhongte"].outcome_loader is number.special_segment_from_row
    assert mechanisms.PREDICTION_CONFIGS["siduanzhongte"].content_formatter is number.format_segment_groups


def test_number_category_preserves_legacy_output_shapes():
    from predict.categories import number

    assert number.special_number_from_row({"res_code": "01,02,03,04,05,06,27"}, None) == "27"
    assert number.special_segment_from_row({"res_code": "01,02,03,04,05,06,27"}, None) == "4段"
    assert number.format_24_numbers(("01", "02"), None) == "01,02"
    assert number.format_split_number_columns(("dan", "shuang"), (2, 1))(
        ("01", "02", "03"), None
    ) == {"dan": "01,02", "shuang": "03"}
    assert number.format_segment_groups(("1段", "2段"), FakeConn()) == [
        "1段|01,02",
        "2段|08,09",
    ]
