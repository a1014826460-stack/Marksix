from __future__ import annotations

from pathlib import Path

from domains.prediction.site_module_blueprints import (
    get_blocked_items_for_site,
    get_blueprint_name_for_site,
    get_required_mode_ids_for_site,
)


def test_twcaibawang_site_uses_dedicated_blueprint_by_domain():
    site = {
        "domain": "www.twcaibawang.com",
        "web_id": 5,
        "lottery_type_id": 1,
    }

    assert get_blueprint_name_for_site(site) == "twcaibawang"


def test_twcaibawang_site_uses_dedicated_blueprint_by_web_id():
    site = {
        "domain": "",
        "web_id": 5,
        "lottery_type_id": 1,
    }

    required = get_required_mode_ids_for_site(site)
    assert required == (
        12,
        26,
        34,
        38,
        49,
        50,
        52,
        54,
        56,
        57,
        58,
        60,
        197,
        472,
        479,
        480,
        481,
        482,
        483,
        484,
    )


def test_twcaibawang_blocked_items_are_exposed_for_admin_audit():
    site = {
        "domain": "twcaibawang.com",
        "web_id": 5,
        "lottery_type_id": 1,
    }

    blocked = get_blocked_items_for_site(site)
    page_titles = {str(item.get("page_title") or "") for item in blocked}

    assert "五肖五码" in page_titles
    assert "一肖一码" in page_titles
    assert "高手榜单" in page_titles
    assert "输尽光" in page_titles
    assert "六尾中特网" in page_titles
    assert "四行中特" in page_titles
    assert "绝杀10码" in page_titles


def test_twcaibawang_frontend_site_defaults_match_backend_target():
    site_config_path = Path(__file__).resolve().parents[4] / "frontend" / "lib" / "sites.ts"
    source = site_config_path.read_text(encoding="utf-8")

    assert 'siteKey: "twcaibawang"' in source
    assert "defaultWebId: 5" in source
    assert "defaultLotteryTypeId: 3" in source
