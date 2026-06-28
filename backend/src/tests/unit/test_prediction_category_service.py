from __future__ import annotations

from domains.prediction.category_service import classify_prediction_config
from domains.prediction.models import PredictionCategory
from predict.common import PredictionConfig, contains_hit
from predict.mechanisms import format_24_numbers, format_size_groups, format_text_history_mapping, format_zodiac_csv


def _config(
    *,
    key: str,
    mode_id: int,
    title: str,
    table_name: str = "mode_payload_1",
    labels: tuple[str, ...] = ("A", "B"),
    formatter=format_zodiac_csv,
) -> PredictionConfig:
    return PredictionConfig(
        key=key,
        title=title,
        default_table=table_name,
        default_modes_id=mode_id,
        labels=labels,
        label_count=1,
        outcome_loader=lambda row, conn: "",
        content_loader=lambda row: "",
        content_parser=lambda content: (),
        content_formatter=formatter,
        hit_checker=contains_hit,
        explanation=(),
    )


def test_classifies_image_modes_by_mode_id():
    config = _config(key="mode474", mode_id=474, title="image")

    assert classify_prediction_config(config) == PredictionCategory.IMAGE


def test_classifies_text_history_mapping_by_formatter_name():
    config = _config(
        key="text",
        mode_id=244,
        title="text",
        table_name="text_history_mappings",
        formatter=format_text_history_mapping("test", 244),
    )

    assert classify_prediction_config(config) == PredictionCategory.TEXT_MAPPING


def test_classifies_size_parity_by_labels():
    config = _config(
        key="size",
        mode_id=108,
        title="size",
        labels=("大", "小"),
        formatter=format_size_groups,
    )

    assert classify_prediction_config(config) == PredictionCategory.SIZE_PARITY


def test_classifies_number_by_numeric_labels():
    config = _config(
        key="numbers",
        mode_id=24,
        title="24码",
        labels=("01", "02", "03"),
        formatter=format_24_numbers,
    )

    assert classify_prediction_config(config) == PredictionCategory.NUMBER


def test_classifies_structured_mapping_by_pipe_formatter_output():
    config = _config(
        key="structured",
        mode_id=12,
        title="3头中特",
        labels=("0头", "1头"),
        formatter=format_size_groups,
    )

    assert classify_prediction_config(config) == PredictionCategory.STRUCTURED_MAPPING


def test_classifies_mixed_labels_with_dimension_prefixes():
    config = _config(
        key="mixed",
        mode_id=333,
        title="混合",
        labels=("肖:鼠", "尾:1尾"),
    )

    assert classify_prediction_config(config) == PredictionCategory.MIXED


def test_classifies_mixed_labels_with_full_width_dimension_prefixes():
    config = _config(
        key="mixed",
        mode_id=333,
        title="mixed",
        labels=("zodiac：rabbit", "tail：7"),
    )

    assert classify_prediction_config(config) == PredictionCategory.MIXED


def test_classifies_zodiac_as_default_for_zodiac_labels():
    config = _config(
        key="zodiac",
        mode_id=69,
        title="3肖中特",
        labels=("鼠", "牛", "虎"),
    )

    assert classify_prediction_config(config) == PredictionCategory.ZODIAC
