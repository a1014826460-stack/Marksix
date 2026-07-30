from __future__ import annotations

from vendor import homepage_modules


def test_dujia_gongshi_keeps_three_exact_source_dimensions(monkeypatch):
    rows_by_mode = {
        28: [{"year": "2026", "term": "177", "content": "单", "res_code": "01,02,03,04,05,06,37", "res_sx": "鼠,牛,虎,兔,龙,蛇,马", "draw_is_opened": True}],
        57: [{"year": "2026", "term": "177", "content": "大", "res_code": "01,02,03,04,05,06,37", "res_sx": "鼠,牛,虎,兔,龙,蛇,马", "draw_is_opened": True}],
        491: [{"year": "2026", "term": "177", "content": "7尾,1尾,2尾,3尾", "res_code": "01,02,03,04,05,06,37", "res_sx": "鼠,牛,虎,兔,龙,蛇,马", "draw_is_opened": True}],
    }
    monkeypatch.setattr(homepage_modules, "_load_mode_rows", lambda _db, **kwargs: rows_by_mode[kwargs["modes_id"]])
    ctx = homepage_modules.VendorModuleContext(site={}, lottery_type=3, web_id=10, history_limit=6)

    module = homepage_modules._build_dujia_gongshi(ctx, "unused")

    row = module["history"][0]
    assert row["formula"]["parity"] == {"labels": ["单"], "is_correct": True}
    assert row["formula"]["size"] == {"labels": ["大"], "is_correct": True}
    assert row["formula"]["tails"] == {"labels": ["7", "1", "2", "3"], "is_correct": True}
