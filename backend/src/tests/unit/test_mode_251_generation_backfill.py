from __future__ import annotations

from prediction_generation.service import _ensure_mode_251_xiao


def test_mode_251_backfills_xiao_from_content_labels():
    row_data = {
        "content": '["鼠|05,17,29,41","牛|04,16,28,40","虎|03,15,27,39","兔|02,14,26,38"]',
        "xiao": "",
    }

    fixed = _ensure_mode_251_xiao(row_data, row_data["content"])

    assert fixed["xiao"] == "鼠,牛,虎,兔"


def test_mode_251_preserves_existing_xiao():
    row_data = {
        "content": '["鼠|05,17,29,41","牛|04,16,28,40"]',
        "xiao": "鼠,牛,虎,兔",
    }

    fixed = _ensure_mode_251_xiao(row_data, row_data["content"])

    assert fixed["xiao"] == "鼠,牛,虎,兔"
