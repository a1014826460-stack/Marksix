from __future__ import annotations

from public.api import serialize_public_history_row


def test_serialize_public_history_row_exposes_image_url():
    row = {
        "year": "2026",
        "term": "123",
        "title": "台湾跑马图（带图）",
        "content": "01 02 03",
        "image_url": "/data/Images/mode_478/prediction/mode_478_type3_2026123_web4.jpg",
        "web_id": 4,
        "res_code": "",
        "res_sx": "",
        "draw_is_opened": False,
    }

    result = serialize_public_history_row(row)

    assert result["image_url"] == row["image_url"]
    assert result["raw"]["image_url"] == row["image_url"]
