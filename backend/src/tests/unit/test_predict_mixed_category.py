from __future__ import annotations

from predict import mechanisms
from predict.categories import mixed


def test_mixed_category_reexports_mechanism_functions():
    assert mechanisms.parse_mixed_dimension_content is mixed.parse_mixed_dimension_content
    assert mechanisms.mixed_dimension_contains_hit is mixed.mixed_dimension_contains_hit
    assert mechanisms.mixed_dimension_excludes_hit is mixed.mixed_dimension_excludes_hit


def test_mixed_mechanism_wrapper_binds_tail_parser():
    loader = mechanisms.mixed_xiao_tail_content_loader()

    assert loader({"xiao": "", "wei": "7尾"}) == "尾:7尾"


def test_mixed_category_counts_any_dimension_as_hit():
    assert mixed.mixed_dimension_contains_hit("肖:rat|尾:7尾", ("尾:7尾",))
    assert mixed.mixed_dimension_contains_hit("肖:rat|尾:7尾", ("肖:rat",))
    assert not mixed.mixed_dimension_contains_hit("肖:rat|尾:7尾", ("肖:ox", "尾:8尾"))
    assert mixed.mixed_dimension_excludes_hit("肖:rat|尾:7尾", ("肖:ox", "尾:8尾"))
