from __future__ import annotations

from predict.mechanisms import get_prediction_config


def test_twssz_five_no_hit_mechanism_has_exact_number_exclusion_contract():
    config = get_prediction_config("wuzhong5ma")

    assert config.default_modes_id == 485
    assert config.default_table == "mode_payload_485"
    assert config.label_count == 5
    assert config.content_formatter(("01", "02", "03", "04", "05"), None) == "01,02,03,04,05"
    assert config.hit_checker("06", ("01", "02", "03", "04", "05")) is True
    assert config.hit_checker("05", ("01", "02", "03", "04", "05")) is False
