from __future__ import annotations

from typing import Any

from predict.common import load_fixed_value_map, special_code_from_res_code


SEGMENT_ORDER = tuple(f"{index}段" for index in range(1, 8))


def special_number_from_row(row: Any, _: Any) -> str:
    return special_code_from_res_code(row["res_code"] or "")


def format_24_numbers(labels: tuple[str, ...], _: Any) -> str:
    return ",".join(labels)


def special_segment_from_row(row: Any, _: Any) -> str:
    number = int(special_code_from_res_code(row["res_code"] or ""))
    return f"{((number - 1) // 7) + 1}段"


def format_segment_groups(labels: tuple[str, ...], conn: Any) -> list[str]:
    mapping = load_fixed_value_map(conn, "7段", labels)
    if not any(mapping.values()):
        mapping = {
            f"{segment}段": tuple(
                f"{number:02d}" for number in range((segment - 1) * 7 + 1, segment * 7 + 1)
            )
            for segment in range(1, 8)
        }
    return [f"{label}|{','.join(mapping.get(label, ()))}" for label in labels]


def format_split_number_columns(columns: tuple[str, ...], widths: tuple[int, ...]):
    def formatter(labels: tuple[str, ...], _: Any) -> dict[str, str]:
        result: dict[str, str] = {}
        index = 0
        for column, width in zip(columns, widths):
            result[column] = ",".join(labels[index:index + width])
            index += width
        return result

    return formatter
