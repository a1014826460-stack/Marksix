from __future__ import annotations

from predict import mechanisms
from predict.categories import size_parity


class FakeConn:
    def table_exists(self, _table_name):
        return False

    def table_columns(self, _table_name):
        return ()

    def execute(self, *_args, **_kwargs):
        class Cursor:
            def fetchone(self):
                return None

            def fetchall(self):
                return []

        return Cursor()


def test_size_parity_category_reexports_mechanism_functions():
    assert mechanisms.special_parity_from_row is size_parity.special_parity_from_row
    assert mechanisms.special_size_from_row is size_parity.special_size_from_row
    assert mechanisms.special_wave_from_row is size_parity.special_wave_from_row
    assert mechanisms.special_half_wave_from_row is size_parity.special_half_wave_from_row
    assert mechanisms.format_size_groups is size_parity.format_size_groups
    assert mechanisms.format_parity_groups is size_parity.format_parity_groups


def test_size_parity_category_fallbacks_without_fixed_data():
    row = {"res_code": "01,02,03,04,05,06,27", "res_color": "red,blue,green"}
    conn = FakeConn()

    assert size_parity.special_parity_from_row(row, conn) == "单"
    assert size_parity.special_size_from_row(row, conn) == "大"
    assert size_parity.special_wave_from_row(row, conn) == "绿波"
    assert size_parity.special_combined_parity_from_row(row, conn) == "合单"
    assert size_parity.special_combined_size_from_row(row, conn) == "合数大"
