from __future__ import annotations

from pathlib import Path

from domains.prediction.site_module_blueprints import (
    get_blocked_items_for_site,
    get_blueprint_name_for_site,
    get_required_mode_ids_for_site,
)
from predict.mechanisms import get_prediction_config


def test_twjinniu_site_uses_dedicated_blueprint_by_domain():
    site = {
        "domain": "www.twjinniu.com",
        "web_id": 7,
        "lottery_type_id": 3,
    }

    assert get_blueprint_name_for_site(site) == "twjinniu"


def test_twjinniu_site_uses_dedicated_blueprint_by_web_id():
    site = {
        "domain": "",
        "web_id": 7,
        "lottery_type_id": 3,
    }

    required = get_required_mode_ids_for_site(site)
    assert required == (
        5,
        12,
        14,
        20,
        15,
        26,
        31,
        38,
        43,
        47,
        48,
        49,
        50,
        53,
        56,
        66,
        72,
        74,
        77,
        78,
        79,
        81,
        83,
        103,
        108,
        110,
        117,
        123,
        132,
        142,
        143,
        144,
        151,
        173,
        180,
        198,
        219,
        279,
        472,
        474,
        476,
        479,
        480,
        481,
        482,
        483,
        484,
    )


def test_twjinniu_blocked_items_are_exposed_for_admin_audit():
    site = {
        "domain": "twjinniu.com",
        "web_id": 7,
        "lottery_type_id": 3,
    }

    blocked = get_blocked_items_for_site(site)
    assert blocked == []


def test_twjinniu_confirmed_mode_configs_are_registered():
    assert int(get_prediction_config("3tou").default_modes_id or 0) == 12
    assert int(get_prediction_config("title_14").default_modes_id or 0) == 14
    assert int(get_prediction_config("danshuang4xiao").default_modes_id or 0) == 31
    assert int(get_prediction_config("pt2xiao").default_modes_id or 0) == 43
    assert int(get_prediction_config("9xzt").default_modes_id or 0) == 49
    assert int(get_prediction_config("yijuzhenyan").default_modes_id or 0) == 50
    assert int(get_prediction_config("juesha1wei").default_modes_id or 0) == 20
    assert int(get_prediction_config("3hang").default_modes_id or 0) == 53
    assert int(get_prediction_config("pt1xiao").default_modes_id or 0) == 56
    assert int(get_prediction_config("dxztt1").default_modes_id or 0) == 108
    assert int(get_prediction_config("title_47").default_modes_id or 0) == 47
    assert int(get_prediction_config("title_48").default_modes_id or 0) == 48
    assert int(get_prediction_config("title_66").default_modes_id or 0) == 66
    assert int(get_prediction_config("title_132").default_modes_id or 0) == 132
    assert int(get_prediction_config("title_143").default_modes_id or 0) == 143
    assert int(get_prediction_config("title_198").default_modes_id or 0) == 198
    assert int(get_prediction_config("title_279").default_modes_id or 0) == 279
    assert int(get_prediction_config("title_74").default_modes_id or 0) == 74
    assert int(get_prediction_config("sxztu").default_modes_id or 0) == 474
    assert int(get_prediction_config("pmtj_image").default_modes_id or 0) == 476
    assert int(get_prediction_config("liuxiao18ma").default_modes_id or 0) == 484
    assert int(get_prediction_config("xiongjiliuxiao").default_modes_id or 0) == 480


def test_twjinniu_frontend_site_defaults_match_backend_target():
    site_config_path = Path(__file__).resolve().parents[4] / "frontend" / "lib" / "sites.ts"
    source = site_config_path.read_text(encoding="utf-8")

    assert 'siteKey: "twjinniu"' in source
    assert "routePath: \"/twjinniu\"" in source
    assert "defaultWebId: 7" in source
    assert "defaultLotteryTypeId: 3" in source
