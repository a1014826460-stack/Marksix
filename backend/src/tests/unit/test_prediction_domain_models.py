from __future__ import annotations

import json

from domains.prediction.models import (
    DrawContext,
    DrawTruth,
    PredictionCategory,
    PredictionOutput,
    PredictionRequest,
)


def test_prediction_domain_models_keep_draw_truth_internal():
    context = DrawContext(
        lottery_type_id=3,
        year=2026,
        term=131,
        is_future=True,
        site_id=7,
        web_id=6,
        mode_id=43,
        mechanism_key="pt3xiao",
    )
    truth = DrawTruth(
        numbers=("01", "02", "03", "04", "05", "06", "07"),
        special_code="07",
        special_zodiac="dog",
        special_color="red",
    )
    request = PredictionRequest(
        category=PredictionCategory.ZODIAC,
        context=context,
        config_key="pt3xiao",
        candidate_labels=("dog", "rat", "ox"),
        truth=truth,
    )
    output = PredictionOutput(
        category=PredictionCategory.ZODIAC,
        row_data={"content": "dog,rat,ox", "res_code": ""},
        hit_target=True,
    )

    assert request.context.web_id == 6
    assert request.truth.special_code == "07"
    assert output.to_public_dict() == {
        "category": "zodiac",
        "row_data": {"content": "dog,rat,ox", "res_code": ""},
        "hit_target": True,
    }
    assert "07" not in json.dumps(output.to_public_dict())


def test_prediction_category_contains_required_plan_categories():
    assert {item.value for item in PredictionCategory} >= {
        "zodiac",
        "image",
        "size_parity",
        "text_mapping",
        "number",
        "structured_mapping",
        "mixed",
    }
