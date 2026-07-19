from __future__ import annotations

from pathlib import Path

from database.schema.prediction import (
    TWCF888_BLOCKED_ITEMS as SCHEMA_TWCF888_BLOCKED_ITEMS,
    TWCF888_REQUIRED_MODE_IDS as SCHEMA_TWCF888_REQUIRED_MODE_IDS,
)
from domains.prediction.site_module_blueprints import (
    TWCF888_BLOCKED_ITEMS,
    TWCF888_KNOWN_UNAVAILABLE_MODE_IDS,
    TWCF888_REQUIRED_MODE_IDS,
    get_blocked_items_for_site,
    get_blueprint_name_for_site,
    get_known_unavailable_mode_ids_for_site,
    get_required_mode_ids_for_site,
)
from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key


EXPECTED_REQUIRED_MODE_IDS = required_mode_ids_for_site_key("twcf888")

EXPECTED_BLOCKED_MODULES = set()


def _twcf888_site(domain: str = "www.twcf888.com") -> dict[str, object]:
    return {
        "domain": domain,
        "web_id": 8,
        "lottery_type_id": 3,
    }


def test_twcf888_blueprint_matches_by_domain_and_web_id():
    assert get_blueprint_name_for_site(_twcf888_site()) == "twcf888"
    assert get_blueprint_name_for_site(_twcf888_site("twcf888.com")) == "twcf888"
    assert get_blueprint_name_for_site({"domain": "", "web_id": 8, "lottery_type_id": 3}) == "twcf888"


def test_twcf888_required_mode_ids_are_fixed():
    assert TWCF888_REQUIRED_MODE_IDS == EXPECTED_REQUIRED_MODE_IDS
    assert SCHEMA_TWCF888_REQUIRED_MODE_IDS == EXPECTED_REQUIRED_MODE_IDS
    assert get_required_mode_ids_for_site(_twcf888_site()) == EXPECTED_REQUIRED_MODE_IDS


def test_twcf888_known_unavailable_mode_ids_are_empty():
    assert TWCF888_KNOWN_UNAVAILABLE_MODE_IDS == ()
    assert get_known_unavailable_mode_ids_for_site(_twcf888_site()) == ()


def test_twcf888_blocked_items_are_fixed():
    blocked_modules = {item["frontend_module"] for item in TWCF888_BLOCKED_ITEMS}
    schema_blocked_modules = {item["frontend_module"] for item in SCHEMA_TWCF888_BLOCKED_ITEMS}
    resolved_blocked_modules = {
        item["frontend_module"] for item in get_blocked_items_for_site(_twcf888_site())
    }

    assert blocked_modules == EXPECTED_BLOCKED_MODULES
    assert schema_blocked_modules == EXPECTED_BLOCKED_MODULES
    assert resolved_blocked_modules == EXPECTED_BLOCKED_MODULES


def test_frontend_site_config_matches_twcf888_defaults():
    sites_file = (
        Path(__file__).resolve().parents[4] / "frontend" / "lib" / "sites.ts"
    )
    text = sites_file.read_text(encoding="utf-8")

    assert 'siteKey: "twcf888"' in text
    assert 'routePath: "/twcf888"' in text
    assert 'vendorIndexPath: "/vendor/twcf888.com/index.html"' in text
    assert 'domains: ["www.twcf888.com", "twcf888.com"]' in text
    assert "defaultWebId: 8" in text
    assert "defaultLotteryTypeId: 3" in text
