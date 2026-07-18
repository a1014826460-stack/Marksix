from __future__ import annotations

from predict import mechanisms
from predict.categories import zodiac


class FakeConn:
    def __init__(self):
        self.rows = [
            {"id": 1, "name": "rat", "code": "01,13,25", "sign": "生肖"},
            {"id": 2, "name": "ox", "code": "02,14,26", "sign": "生肖"},
        ]

    def table_exists(self, table_name):
        return table_name == "fixed_data"

    def execute(self, _sql, params=()):
        sign = params[0] if params else ""
        rows = [row for row in self.rows if row["sign"] == sign]

        class Cursor:
            def fetchall(self_nonlocal):
                return rows

        return Cursor()


def test_zodiac_category_reexports_mechanism_functions():
    assert mechanisms.format_zodiac_csv is zodiac.format_zodiac_csv
    assert mechanisms.format_xiao_pair is zodiac.format_xiao_pair
    assert mechanisms.format_split_zodiac_columns is zodiac.format_split_zodiac_columns
    assert mechanisms.get_zodiac_numbers is zodiac.get_zodiac_numbers
    assert mechanisms.format_zodiac_one_code is zodiac.format_zodiac_one_code
    assert mechanisms.format_zodiac_two_codes is zodiac.format_zodiac_two_codes
    assert mechanisms.format_zodiac_all_codes is zodiac.format_zodiac_all_codes
    assert mechanisms.format_9x12 is zodiac.format_9x12


def test_static_configs_bind_zodiac_category_helpers():
    assert (
        mechanisms.PREDICTION_CONFIGS["pt3xiao"].content_formatter
        is zodiac.format_zodiac_csv
    )
    assert (
        mechanisms.PREDICTION_CONFIGS["sixiao_sima"].content_formatter
        is zodiac.format_zodiac_one_code
    )


def test_zodiac_category_formats_numbers_from_fixed_data():
    conn = FakeConn()

    assert zodiac.get_zodiac_numbers(conn, "rat") == ["01", "13", "25"]
    assert zodiac.format_zodiac_one_code(("rat", "ox"), conn) == ["rat|01", "ox|02"]
    assert zodiac.format_zodiac_two_codes(("rat", "ox"), conn) == ["rat|01,13", "ox|02,14"]
    assert zodiac.format_zodiac_all_codes(("rat",), conn) == ["rat|01,13,25"]


def test_zodiac_category_formats_common_zodiac_shapes():
    assert zodiac.format_zodiac_csv(("rat", "ox"), None) == "rat,ox"
    assert zodiac.format_xiao_pair(tuple(str(index) for index in range(1, 9)), None) == {
        "xiao_1": "1,2,3,4",
        "xiao_2": "5,6,7,8",
    }
    formatter = zodiac.format_split_zodiac_columns(("a", "b"), (1, 2))

    assert formatter(("rat", "ox", "tiger"), None) == {"a": "rat", "b": "ox,tiger"}
