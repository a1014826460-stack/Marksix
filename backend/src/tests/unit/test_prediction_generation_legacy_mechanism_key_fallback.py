from __future__ import annotations

from prediction_generation.service import _resolve_prediction_config_with_mode_fallback


def test_resolve_prediction_config_with_mode_fallback_for_mode_77():
    config, resolved_key, used_fallback = _resolve_prediction_config_with_mode_fallback(
        "title_77",
        77,
    )

    assert used_fallback is True
    assert resolved_key == "shisi_mazhong"
    assert int(config.default_modes_id or 0) == 77
