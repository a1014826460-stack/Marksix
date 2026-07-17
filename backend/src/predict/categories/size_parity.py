from __future__ import annotations

from typing import Any

from predict.common import (
    fixed_label_for_value,
    load_fixed_value_map,
    row_get,
    special_code_from_res_code,
)
from predict.number_maps import (
    HALF_WAVE_NUMBER_MAP,
    HEAD_NUMBER_MAP,
    PARITY_NUMBER_MAP,
    SIZE_NUMBER_MAP,
    TAIL_NUMBER_MAP,
)


def label_for_special_number(
    row: Any,
    conn: Any,
    mapping_key: str,
    fallback: str,
) -> str:
    special_code = special_code_from_res_code(row["res_code"] or "")
    return fixed_label_for_value(conn, mapping_key, special_code) or fallback


def format_fixed_groups(
    mapping_key: str,
    fallback_map: dict[str, list[str]] | None = None,
):
    def formatter(labels: tuple[str, ...], conn: Any) -> list[str]:
        mapping = load_fixed_value_map(conn, mapping_key, labels)
        return [
            f"{label}|{','.join(mapping.get(label, tuple(fallback_map.get(label, ()) if fallback_map else ())))}"
            for label in labels
        ]

    return formatter


def special_head_from_row(row: Any, conn: Any) -> str:
    special_code = special_code_from_res_code(row["res_code"] or "")
    number = int(special_code)
    fallback = "0头" if number < 10 else f"{number // 10}头"
    return label_for_special_number(row, conn, "头", fallback)


def special_tail_from_row(row: Any, conn: Any) -> str:
    special_code = special_code_from_res_code(row["res_code"] or "")
    fallback = f"{int(special_code) % 10}尾"
    return label_for_special_number(row, conn, "尾", fallback)


def special_parity_from_row(row: Any, conn: Any) -> str:
    fallback = "双" if int(special_code_from_res_code(row["res_code"] or "")) % 2 == 0 else "单"
    return label_for_special_number(row, conn, "单双", fallback)


def special_size_from_row(row: Any, conn: Any) -> str:
    fallback = "大" if int(special_code_from_res_code(row["res_code"] or "")) >= 25 else "小"
    return label_for_special_number(row, conn, "大小", fallback)


def special_wave_from_row(row: Any, conn: Any) -> str:
    values = [value.strip() for value in str(row_get(row, "res_color", "") or "").split(",") if value.strip()]
    if values:
        return {"red": "红波", "blue": "蓝波", "green": "绿波"}.get(values[-1], "")

    special_code = special_code_from_res_code(row["res_code"] or "")
    mapped_label = fixed_label_for_value(conn, "波色", special_code)
    if mapped_label:
        return mapped_label
    return ""


def special_half_wave_from_row(row: Any, conn: Any) -> str:
    special_code = special_code_from_res_code(row["res_code"] or "")
    mapped = fixed_label_for_value(conn, "波色单双", special_code)
    if mapped:
        return mapped

    wave = special_wave_from_row(row, conn).removesuffix("波")
    parity = special_parity_from_row(row, conn)
    return f"{wave}{parity}" if wave and parity else ""


def _special_digit_sum(row: Any) -> int:
    number = int(special_code_from_res_code(row["res_code"] or ""))
    return (number // 10) + (number % 10)


def special_combined_parity_from_row(row: Any, _: Any) -> str:
    return "合单" if _special_digit_sum(row) % 2 == 1 else "合双"


def special_combined_size_from_row(row: Any, _: Any) -> str:
    return "合数大" if _special_digit_sum(row) >= 7 else "合数小"


def format_head_groups(labels: tuple[str, ...], conn: Any) -> list[str]:
    return format_fixed_groups("头", HEAD_NUMBER_MAP)(labels, conn)


def format_tail_groups(labels: tuple[str, ...], conn: Any) -> list[str]:
    return format_fixed_groups("尾", TAIL_NUMBER_MAP)(labels, conn)


def format_size_groups(labels: tuple[str, ...], conn: Any) -> list[str]:
    return format_fixed_groups("大小", SIZE_NUMBER_MAP)(labels, conn)


def format_half_wave_groups(labels: tuple[str, ...], conn: Any) -> list[str]:
    return format_fixed_groups("波色单双", HALF_WAVE_NUMBER_MAP)(labels, conn)


def format_parity_groups(labels: tuple[str, ...], conn: Any) -> list[str]:
    return format_fixed_groups("单双", PARITY_NUMBER_MAP)(labels, conn)
