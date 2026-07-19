from __future__ import annotations

from pathlib import Path

from domains.prediction.site_module_blueprints import (
    get_blocked_items_for_site,
    get_blueprint_name_for_site,
    get_required_mode_ids_for_site,
)
from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key


def test_twcaibawang_site_uses_dedicated_blueprint_by_domain():
    site = {
        "domain": "www.twcaibawang.com",
        "web_id": 5,
        "lottery_type_id": 1,
    }

    assert get_blueprint_name_for_site(site) == "twcaibawang"


def test_database_blueprint_profile_takes_priority_over_domain_guess():
    site = {
        "domain": "www.example.com",
        "web_id": 99,
        "lottery_type_id": 3,
        "blueprint_name": "twcaibawang",
        "blueprint_required_mode_ids_json": "[12,26,197]",
        "blueprint_known_unavailable_mode_ids_json": "[]",
        "blueprint_blocked_items_json": '[{\"page_title\":\"五肖五码\",\"status\":\"blocked_exact_payload_mapping\"}]',
    }

    assert get_blueprint_name_for_site(site) == "twcaibawang"
    assert get_required_mode_ids_for_site(site) == (12, 26, 197)
    assert get_blocked_items_for_site(site)[0]["page_title"] == "五肖五码"


def test_twcaibawang_site_uses_dedicated_blueprint_by_web_id():
    site = {
        "domain": "",
        "web_id": 5,
        "lottery_type_id": 1,
    }

    assert get_required_mode_ids_for_site(site) == required_mode_ids_for_site_key("twcaibawang")


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
