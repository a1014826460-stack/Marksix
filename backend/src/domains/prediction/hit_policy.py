"""Prediction hit semantics for domain handlers.

The functions in this module are pure and do not query databases. They convert
internal draw truth into category-specific hit labels. Full draw numbers are
never returned; only the minimal labels needed for hit checks are exposed.
"""

from __future__ import annotations

from .models import PredictionCategory, PredictionRequest


def _normalize_label(label: str) -> str:
    return str(label or "").strip().replace("：", ":")


def _special_tail(code: str) -> str:
    text = str(code or "").strip()
    if not text:
        return ""
    try:
        return str(int(text) % 10)
    except ValueError:
        return text[-1:]


def _special_head(code: str) -> str:
    text = str(code or "").strip()
    if not text:
        return ""
    try:
        return str(int(text) // 10)
    except ValueError:
        return text[:1]


def truth_labels_for_request(request: PredictionRequest) -> tuple[str, ...]:
    truth = request.truth
    if not truth:
        return ()

    category = request.category
    code = str(truth.special_code or "").strip()
    zodiac = str(truth.special_zodiac or "").strip()
    color = str(truth.special_color or "").strip()

    if category == PredictionCategory.MIXED:
        labels = [
            f"zodiac:{zodiac}" if zodiac else "",
            f"number:{code}" if code else "",
            f"tail:{_special_tail(code)}" if code else "",
            f"head:{_special_head(code)}" if code else "",
            f"color:{color}" if color else "",
        ]
        return tuple(label for label in labels if label)
    if category == PredictionCategory.ZODIAC:
        return (zodiac,) if zodiac else ()
    if category == PredictionCategory.NUMBER:
        return (code,) if code else ()
    if category == PredictionCategory.SIZE_PARITY:
        if not code:
            return ()
        try:
            value = int(code)
        except ValueError:
            return ()
        return (
            "big" if value >= 25 else "small",
            "odd" if value % 2 else "even",
        )
    return tuple(label for label in (zodiac, code, color) if label)


def is_prediction_hit(request: PredictionRequest, predicted_labels: tuple[str, ...]) -> bool:
    truth_labels = {_normalize_label(label) for label in truth_labels_for_request(request)}
    predictions = {_normalize_label(label) for label in predicted_labels}
    return bool(truth_labels & predictions)
