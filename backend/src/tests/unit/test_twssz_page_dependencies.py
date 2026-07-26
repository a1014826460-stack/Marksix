from __future__ import annotations

from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key


def test_twssz_confirmed_page_mappings_are_authorized():
    mode_ids = set(required_mode_ids_for_site_key("twssz"))

    assert {20, 34, 38, 43, 47, 48, 53, 54, 57, 58, 66, 69, 117, 123, 132, 143, 472, 473, 485}.issubset(mode_ids)
