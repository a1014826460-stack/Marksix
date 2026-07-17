from __future__ import annotations

from typing import Any, Callable

from predict.common import parse_zodiac_content, row_get, special_zodiac_from_number_map


def mixed_xiao_tail_content_loader(
    xiao_column: str = "xiao",
    tail_column: str = "wei",
    *,
    tail_parser: Callable[[str], tuple[str, ...]],
):
    def loader(row: Any) -> str:
        zodiac_labels = [f"肖:{label}" for label in parse_zodiac_content(str(row_get(row, xiao_column, "") or ""))]
        tail_labels = [f"尾:{label}" for label in tail_parser(str(row_get(row, tail_column, "") or ""))]
        return ",".join(zodiac_labels + tail_labels)

    return loader


def parse_mixed_dimension_content(content: str) -> tuple[str, ...]:
    return tuple(value.strip() for value in content.split(",") if value.strip())


def mixed_xiao_tail_outcome_from_row(row: Any, conn: Any, *, tail_outcome_loader) -> str:
    return f"肖:{special_zodiac_from_number_map(row, conn)}|尾:{tail_outcome_loader(row, conn)}"


def mixed_dimension_contains_hit(outcome: str, labels: tuple[str, ...]) -> bool:
    return any(value in labels for value in str(outcome or "").split("|") if value)


def mixed_dimension_excludes_hit(outcome: str, labels: tuple[str, ...]) -> bool:
    return not mixed_dimension_contains_hit(outcome, labels)
