from __future__ import annotations

import pytest

from predict.common import PredictionConfig, contains_hit
from predict.registry import PredictionRegistry


def _config(key: str, mode_id: int) -> PredictionConfig:
    return PredictionConfig(
        key=key,
        title=f"title {key}",
        default_table=f"mode_payload_{mode_id}",
        default_modes_id=mode_id,
        labels=("a", "b"),
        label_count=1,
        outcome_loader=lambda row, conn: "",
        content_loader=lambda row: "",
        content_parser=lambda content: (),
        content_formatter=lambda labels, conn: ",".join(labels),
        hit_checker=contains_hit,
        explanation=(),
    )


def test_prediction_registry_lists_and_gets_configs_with_status():
    registry = PredictionRegistry({"b": _config("b", 2), "a": _config("a", 1)})

    assert registry.supported_keys() == ("a", "b")
    assert registry.get("a").default_modes_id == 1
    assert registry.list_configs(status_map={"b": 0}) == [
        {
            "key": "a",
            "title": "title a",
            "default_modes_id": 1,
            "default_table": "mode_payload_1",
            "status": 1,
        },
        {
            "key": "b",
            "title": "title b",
            "default_modes_id": 2,
            "default_table": "mode_payload_2",
            "status": 0,
        },
    ]


def test_prediction_registry_raises_value_error_for_unknown_key():
    registry = PredictionRegistry({"a": _config("a", 1)})

    with pytest.raises(ValueError) as exc:
        registry.get("missing")

    assert "missing" in str(exc.value)
    assert "a" in str(exc.value)
