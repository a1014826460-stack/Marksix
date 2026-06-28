"""Prediction play category classification.

This module is intentionally pure: it does not query databases and only reads
the already-loaded prediction configuration. The category is used as the
stable boundary for future handler migration.
"""

from __future__ import annotations

from typing import Any

from .models import PredictionCategory


IMAGE_MODE_IDS = {474, 475, 476, 478}
SIZE_PARITY_LABELS = {
    "大",
    "小",
    "单",
    "双",
    "合大",
    "合小",
    "合单",
    "合双",
    "红波",
    "蓝波",
    "绿波",
    "红单",
    "红双",
    "蓝单",
    "蓝双",
    "绿单",
    "绿双",
}
ZODIAC_LABELS = {
    "鼠",
    "牛",
    "虎",
    "兔",
    "龙",
    "蛇",
    "马",
    "羊",
    "猴",
    "鸡",
    "狗",
    "猪",
}
STRUCTURED_MARKERS = ("头", "尾", "行", "段", "家", "野", "琴", "棋", "书", "画", "季", "门")


def _labels(config: Any) -> tuple[str, ...]:
    return tuple(str(label or "").strip() for label in getattr(config, "labels", ()) if str(label or "").strip())


def _formatter_name(config: Any) -> str:
    formatter = getattr(config, "content_formatter", None)
    name = getattr(formatter, "__name__", "")
    qualname = getattr(formatter, "__qualname__", "")
    return f"{name} {qualname}".lower()


def _has_text_mapping_shape(config: Any) -> bool:
    table_name = str(getattr(config, "default_table", "") or "").lower()
    title = str(getattr(config, "title", "") or "").lower()
    formatter_name = _formatter_name(config)
    return (
        "text_history" in table_name
        or "text_history" in formatter_name
        or "text_history" in title
    )


def _has_mixed_dimension(labels: tuple[str, ...]) -> bool:
    prefixes = {label.split(":", 1)[0] for label in labels if ":" in label}
    return len(prefixes) >= 2


def _is_number(labels: tuple[str, ...]) -> bool:
    return bool(labels) and all(label.isdigit() for label in labels)


def _is_zodiac(labels: tuple[str, ...]) -> bool:
    return bool(labels) and all(label in ZODIAC_LABELS for label in labels)


def _is_size_parity(labels: tuple[str, ...]) -> bool:
    return bool(labels) and all(label in SIZE_PARITY_LABELS for label in labels)


def _is_structured(labels: tuple[str, ...]) -> bool:
    return any("|" in label for label in labels) or any(
        marker in label for label in labels for marker in STRUCTURED_MARKERS
    )


def classify_prediction_config(config: Any) -> PredictionCategory:
    mode_id = int(getattr(config, "default_modes_id", 0) or 0)
    labels = _labels(config)

    if mode_id in IMAGE_MODE_IDS:
        return PredictionCategory.IMAGE
    if _has_text_mapping_shape(config):
        return PredictionCategory.TEXT_MAPPING
    if _has_mixed_dimension(labels):
        return PredictionCategory.MIXED
    if _is_size_parity(labels):
        return PredictionCategory.SIZE_PARITY
    if _is_number(labels):
        return PredictionCategory.NUMBER
    if _is_zodiac(labels):
        return PredictionCategory.ZODIAC
    if _is_structured(labels):
        return PredictionCategory.STRUCTURED_MAPPING
    return PredictionCategory.MIXED
