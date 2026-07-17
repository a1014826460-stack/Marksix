from __future__ import annotations

from typing import Any
import json

from predict.common import load_fixed_value_map


def format_zodiac_csv(labels: tuple[str, ...], _: Any) -> str:
    return ",".join(labels)


def format_xiao_pair(labels: tuple[str, ...], _: Any) -> dict[str, str]:
    return {
        "xiao_1": ",".join(labels[:4]),
        "xiao_2": ",".join(labels[4:8]),
    }


def format_split_zodiac_columns(
    columns: tuple[str, ...],
    widths: tuple[int, ...],
    codes_per_label: int = 0,
):
    def formatter(labels: tuple[str, ...], conn: Any) -> dict[str, str]:
        result: dict[str, str] = {}
        index = 0
        for column, width in zip(columns, widths):
            group_labels = labels[index:index + width]
            index += width
            if codes_per_label > 0:
                result[column] = json.dumps(
                    [
                        f"{label}|{','.join(get_zodiac_numbers(conn, label)[:codes_per_label])}"
                        for label in group_labels
                    ],
                    ensure_ascii=False,
                )
            else:
                result[column] = ",".join(group_labels)
        return result

    return formatter


def get_zodiac_numbers(conn: Any, zodiac: str) -> list[str]:
    mapping = load_fixed_value_map(conn, "生肖", (zodiac,))
    return list(mapping.get(zodiac, ()))


def format_zodiac_one_code(labels: tuple[str, ...], conn: Any) -> list[str]:
    result: list[str] = []
    for label in labels:
        numbers = get_zodiac_numbers(conn, label)
        result.append(f"{label}|{numbers[0] if numbers else ''}")
    return result


def format_zodiac_two_codes(labels: tuple[str, ...], conn: Any) -> list[str]:
    result: list[str] = []
    for label in labels:
        numbers = get_zodiac_numbers(conn, label)[:2]
        result.append(f"{label}|{','.join(numbers)}")
    return result


def format_zodiac_all_codes(labels: tuple[str, ...], conn: Any) -> list[str]:
    result: list[str] = []
    for label in labels:
        numbers = get_zodiac_numbers(conn, label)
        result.append(f"{label}|{','.join(numbers)}")
    return result


def format_9x12(labels: tuple[str, ...], conn: Any) -> dict[str, str]:
    selected_codes: list[str] = []
    per_zodiac_numbers = {label: get_zodiac_numbers(conn, label) for label in labels}
    index = 0
    while len(selected_codes) < 12 and index < 5:
        for label in labels:
            numbers = per_zodiac_numbers.get(label, [])
            if index < len(numbers):
                selected_codes.append(numbers[index])
                if len(selected_codes) == 12:
                    break
        index += 1
    return {
        "xiao": ",".join(labels),
        "code": ",".join(selected_codes),
    }


def format_xiao_code_columns(
    xiao_column: str,
    code_column: str,
    code_count: int,
):
    def formatter(labels: tuple[str, ...], conn: Any) -> dict[str, str]:
        all_zodiac_map = load_fixed_value_map(conn, "生肖")
        per_zodiac_numbers: dict[str, list[str]] = {}
        for label in labels:
            per_zodiac_numbers[label] = list(all_zodiac_map.get(label, ()))

        selected_codes: list[str] = []
        index = 0
        while len(selected_codes) < code_count and index < 5:
            for label in labels:
                numbers = per_zodiac_numbers.get(label, [])
                if index < len(numbers):
                    code = numbers[index]
                    if code not in selected_codes:
                        selected_codes.append(code)
                        if len(selected_codes) == code_count:
                            break
            index += 1

        return {
            xiao_column: ",".join(labels),
            code_column: ",".join(selected_codes),
        }

    return formatter
