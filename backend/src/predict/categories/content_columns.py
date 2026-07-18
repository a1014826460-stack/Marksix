from __future__ import annotations

import re
from typing import Any, Callable

from predict.common import normalize_zodiac_label, parse_json_or_plain_content, row_get


def jiexi_content_from_row(row: Any) -> str:
    return str(row_get(row, "jiexi", "") or "")


def tail_code_content_from_row(row: Any) -> str:
    return str(row_get(row, "code", "") or "")


def xiao_code_content_from_row(row: Any) -> str:
    return str(row_get(row, "xiao", "") or "")


def black_white_content_from_row(row: Any) -> str:
    values = [
        str(row_get(row, "hei", "") or "").strip(),
        str(row_get(row, "bai", "") or "").strip(),
    ]
    return ",".join(value for value in values if value)


def join_columns_content_loader(columns: tuple[str, ...]):
    def loader(row: Any) -> str:
        return ",".join(
            str(row_get(row, column, "") or "").strip()
            for column in columns
            if str(row_get(row, column, "") or "").strip()
        )

    return loader


def parsed_columns_content_loader(columns: tuple[str, ...], value_parser: Callable[[str], tuple[str, ...]]):
    def loader(row: Any) -> str:
        labels: list[str] = []
        for column in columns:
            labels.extend(value_parser(str(row_get(row, column, "") or "")))
        return ",".join(labels)

    return loader


def tail_columns_content_loader(columns: tuple[str, ...]):
    def loader(row: Any) -> str:
        labels: list[str] = []
        for column in columns:
            for value in re.findall(r"\d", str(row_get(row, column, "") or "")):
                label = f"{int(value)}尾"
                if label not in labels:
                    labels.append(label)
        return ",".join(labels)

    return loader


def parse_tail_digit_content(content: str) -> tuple[str, ...]:
    chinese_digits = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    labels: list[str] = []
    for item in parse_json_or_plain_content(content):
        text = item.split("|", 1)[0] if "|" in item else item
        for value in re.findall(r"\d", text):
            label = f"{int(value)}尾"
            if label not in labels:
                labels.append(label)
        for value in re.findall(r"[零一二两三四五六七八九]", text):
            label = f"{chinese_digits[value]}尾"
            if label not in labels:
                labels.append(label)
    return tuple(labels)


def parse_zodiac_chars(content: str) -> tuple[str, ...]:
    values = [normalize_zodiac_label(value) for value in re.findall(r"[鼠牛虎兔龍蛇马馬羊猴鸡雞狗猪豬]", content or "")]
    return tuple(dict.fromkeys(values))


def parse_wave_chars(content: str) -> tuple[str, ...]:
    labels: list[str] = []
    for value in re.findall(r"[红蓝绿]", content or ""):
        label = f"{value}波"
        if label not in labels:
            labels.append(label)
    return tuple(labels)


def parse_literal_label_content(content: str) -> tuple[str, ...]:
    labels: list[str] = []
    for item in parse_json_or_plain_content(content):
        value = item.split("|", 1)[0].strip() if "|" in item else str(item or "").strip()
        if value and value not in labels:
            labels.append(value)
    return tuple(labels) or ((str(content or "").strip(),) if str(content or "").strip() else ())
