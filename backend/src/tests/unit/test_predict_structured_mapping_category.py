from __future__ import annotations

from predict import mechanisms
from predict.categories import structured_mapping


def test_structured_mapping_category_reexports_mechanism_functions():
    assert mechanisms.category_outcome_from_map is structured_mapping.category_outcome_from_map
    assert mechanisms.build_pipe_value_map is structured_mapping.build_pipe_value_map
    assert mechanisms.format_dynamic_pipe_groups is structured_mapping.format_dynamic_pipe_groups


def test_structured_mapping_category_finds_outcome_from_mapping():
    mapping = {"red": ("01", "02"), "blue": ("03",)}

    assert structured_mapping.category_outcome_from_map("03", mapping, ("red", "blue")) == "blue"
    assert structured_mapping.category_outcome_from_map("09", mapping, ("red", "blue")) == ""


def test_structured_mapping_builds_pipe_map_from_history(monkeypatch):
    monkeypatch.setattr(structured_mapping, "load_fixed_value_map", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(structured_mapping, "table_fixed_mapping_keys", {})
    monkeypatch.setattr(structured_mapping, "find_fixed_data_sign_for_labels", lambda *_args: None)
    monkeypatch.setattr(
        structured_mapping.predict_repository,
        "load_non_empty_column_values",
        lambda *_args: ["red|01,02", "blue|03"],
    )

    mapping = structured_mapping.build_pipe_value_map(object(), "mode_payload_1", ("red", "blue"))

    assert mapping == {"red": ("01", "02"), "blue": ("03",)}
