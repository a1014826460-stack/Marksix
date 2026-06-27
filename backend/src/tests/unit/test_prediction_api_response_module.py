from __future__ import annotations

from admin import prediction as admin_prediction
from domains.prediction import api_response
from prediction_generation import service as prediction_generation_service


def test_admin_prediction_reexports_api_response_builder():
    assert admin_prediction.build_prediction_api_response is api_response.build_prediction_api_response


def test_admin_prediction_reexports_display_text_normalizer():
    assert admin_prediction.normalize_prediction_display_text is api_response.normalize_prediction_display_text


def test_admin_prediction_does_not_keep_legacy_api_response_copy():
    assert not hasattr(admin_prediction, "_legacy_build_prediction_api_response")
    assert not hasattr(admin_prediction, "_legacy_normalize_prediction_display_text")


def test_admin_prediction_reexports_opened_draw_loader():
    assert (
        admin_prediction.list_opened_draws_in_issue_range
        is prediction_generation_service.list_opened_draws_in_issue_range
    )
