from __future__ import annotations

import ast
from pathlib import Path


MECHANISMS_PATH = Path(__file__).resolve().parents[2] / "predict" / "mechanisms.py"


def test_extracted_category_helpers_are_not_redefined_in_mechanisms():
    tree = ast.parse(MECHANISMS_PATH.read_text(encoding="utf-8-sig"))
    local_functions = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    extracted_helpers = {
        "label_for_special_number",
        "format_fixed_groups",
        "special_head_from_row",
        "special_tail_from_row",
        "special_parity_from_row",
        "special_size_from_row",
        "special_half_wave_from_row",
        "special_wave_from_row",
        "special_combined_parity_from_row",
        "special_combined_size_from_row",
        "format_head_groups",
        "format_tail_groups",
        "format_size_groups",
        "format_half_wave_groups",
        "format_parity_groups",
        "parse_mixed_dimension_content",
        "mixed_dimension_contains_hit",
        "mixed_dimension_excludes_hit",
        "get_zodiac_numbers",
        "format_zodiac_one_code",
        "format_zodiac_two_codes",
        "format_zodiac_all_codes",
        "format_9x12",
        "format_zodiac_csv",
        "format_xiao_pair",
        "format_split_zodiac_columns",
        "format_xiao_code_columns",
        "special_number_from_row",
        "format_24_numbers",
        "special_segment_from_row",
        "format_segment_groups",
        "format_split_number_columns",
        "build_qinqi_value_map",
        "make_pipe_category_outcome",
        "qinqi_outcome_from_row",
        "format_zodiac_groups",
        "format_qinqi_content",
        "format_window_content",
        "_latest_window_metadata",
        "jiexi_content_from_row",
        "tail_code_content_from_row",
        "xiao_code_content_from_row",
        "black_white_content_from_row",
        "join_columns_content_loader",
        "parsed_columns_content_loader",
        "tail_columns_content_loader",
        "parse_tail_digit_content",
        "parse_zodiac_chars",
        "parse_wave_chars",
        "parse_literal_label_content",
    }

    assert not (local_functions & extracted_helpers)
