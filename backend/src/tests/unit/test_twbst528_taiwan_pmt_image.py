from __future__ import annotations

from vendor import homepage_modules


def test_twbst528_taiwan_pmt_image_returns_only_its_latest_site_image(monkeypatch):
    rows = [
        {
            "year": "2026",
            "term": "179",
            "web": 10,
            "type": 3,
            "content": "鼠|01,13",
            "image_url": "/uploads/predictions/mode_478_type3_2026179_web10.jpg",
            "draw_is_opened": False,
        },
        {
            "year": "2026",
            "term": "178",
            "web": 10,
            "type": 3,
            "content": "牛|02,14",
            "image_url": "/uploads/predictions/mode_478_type3_2026178_web10.jpg",
            "draw_is_opened": True,
        },
    ]
    monkeypatch.setattr(homepage_modules, "_load_mode_rows", lambda _db, **_kwargs: rows)
    ctx = homepage_modules.VendorModuleContext(site={}, lottery_type=3, web_id=10, history_limit=6)

    module = homepage_modules._build_tw_pmt_image(ctx, "unused")

    assert module["module_key"] == "tw_pmt_image"
    assert module["history"] == [
        {
            "issue": "2026179",
            "year": "2026",
            "term": "179",
            "image_url": "/uploads/predictions/mode_478_type3_2026179_web10.jpg",
            "result": {
                "res_code": "",
                "res_sx": "",
                "res_color": "",
                "result_text": "待开奖",
                "is_opened": False,
            },
            "is_opened": False,
            "is_correct": None,
            "raw": {"source_mode_ids": [478]},
        }
    ]


def test_twbst528_taiwan_pmt_image_normalizes_generated_image_path(monkeypatch):
    monkeypatch.setattr(
        homepage_modules,
        "_load_mode_rows",
        lambda _db, **_kwargs: [
            {
                "year": "2026",
                "term": "188",
                "image_url": "/data/Images/mode_478/prediction/mode_478_type3_2026188_web10.jpg",
                "draw_is_opened": False,
            }
        ],
    )
    ctx = homepage_modules.VendorModuleContext(site={}, lottery_type=3, web_id=10, history_limit=6)

    module = homepage_modules._build_tw_pmt_image(ctx, "unused")

    assert module["history"][0]["image_url"] == "/uploads/mode_478/prediction/mode_478_type3_2026188_web10.jpg"
