from __future__ import annotations

from typing import Any, Callable

from domains.prediction import predict_repository
from predict.common import load_fixed_value_map, parse_json_or_plain_content


table_fixed_mapping_keys: dict[str, str] = {}
find_fixed_data_sign_for_labels: Callable[[Any, tuple[str, ...]], str | None] = lambda _conn, _labels: None


def build_pipe_value_map(
    conn: Any,
    table_name: str,
    labels: tuple[str, ...],
) -> dict[str, tuple[str, ...]]:
    fixed_mapping_key = table_fixed_mapping_keys.get(table_name)
    if fixed_mapping_key:
        fixed_mapping = load_fixed_value_map(conn, fixed_mapping_key, labels)
        if fixed_mapping and any(fixed_mapping.values()):
            return fixed_mapping

    guessed_sign = find_fixed_data_sign_for_labels(conn, labels)
    if guessed_sign:
        fixed_mapping = load_fixed_value_map(conn, guessed_sign, labels)
        if fixed_mapping and any(fixed_mapping.values()):
            return fixed_mapping

    result: dict[str, set[str]] = {label: set() for label in labels}
    for content in predict_repository.load_non_empty_column_values(conn, table_name, "content"):
        items = parse_json_or_plain_content(content)
        if "|" in content and not str(content).lstrip().startswith("["):
            items = [str(content)]
        for item in items:
            if "|" not in item:
                continue
            label, raw_values = item.split("|", 1)
            label = label.strip()
            if label not in result:
                continue
            values = [value.strip() for value in raw_values.split(",") if value.strip()]
            result[label].update(values)
    return {label: tuple(sorted(values)) for label, values in result.items()}


def category_outcome_from_map(
    value: str,
    mapping: dict[str, tuple[str, ...]],
    labels: tuple[str, ...],
) -> str:
    for label in labels:
        if value in mapping.get(label, ()):
            return label
    return ""


def format_dynamic_pipe_groups(table_name: str):
    def formatter(selected: tuple[str, ...], conn: Any) -> list[str]:
        mapping = build_pipe_value_map(conn, table_name, selected)
        return [f"{label}|{','.join(mapping.get(label, ()))}" for label in selected]

    return formatter
