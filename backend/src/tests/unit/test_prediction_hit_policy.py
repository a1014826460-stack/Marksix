from __future__ import annotations

from domains.prediction.hit_policy import is_prediction_hit, truth_labels_for_request
from domains.prediction.models import DrawContext, DrawTruth, PredictionCategory, PredictionRequest


def _request(category: PredictionCategory, *, candidate_labels: tuple[str, ...] = ()) -> PredictionRequest:
    return PredictionRequest(
        category=category,
        context=DrawContext(
            lottery_type_id=3,
            year=2026,
            term=131,
            is_future=True,
            site_id=7,
            web_id=6,
            mode_id=333,
            mechanism_key="mixed",
        ),
        config_key="mixed",
        candidate_labels=candidate_labels,
        truth=DrawTruth(
            numbers=("01", "02", "03", "04", "05", "06", "27"),
            special_code="27",
            special_zodiac="rabbit",
            special_color="red",
        ),
    )


def test_mixed_truth_labels_include_all_supported_dimensions_without_raw_draw_numbers():
    labels = truth_labels_for_request(_request(PredictionCategory.MIXED))

    assert labels == ("zodiac:rabbit", "number:27", "tail:7", "head:2", "color:red")


def test_mixed_prediction_hits_when_any_dimension_matches():
    request = _request(PredictionCategory.MIXED)

    assert is_prediction_hit(request, ("tail:7",)) is True
    assert is_prediction_hit(request, ("zodiac:rabbit",)) is True
    assert is_prediction_hit(request, ("number:27",)) is True
    assert is_prediction_hit(request, ("head:2",)) is True
    assert is_prediction_hit(request, ("color:red",)) is True
    assert is_prediction_hit(request, ("tail:3", "zodiac:rat")) is False


def test_mixed_prediction_supports_full_width_dimension_separator():
    request = _request(PredictionCategory.MIXED)

    assert is_prediction_hit(request, ("tail：7",)) is True
    assert is_prediction_hit(request, ("zodiac：rabbit",)) is True


def test_zodiac_prediction_still_uses_special_zodiac_only():
    request = _request(PredictionCategory.ZODIAC)

    assert truth_labels_for_request(request) == ("rabbit",)
    assert is_prediction_hit(request, ("rabbit",)) is True
    assert is_prediction_hit(request, ("27", "red")) is False
