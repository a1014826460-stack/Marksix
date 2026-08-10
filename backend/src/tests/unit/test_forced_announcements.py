from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.errors import ConflictError
from app_http.site_context import resolve_site_context
from db import connect
from domains.announcements.service import (
    create_forced_announcement,
    delete_forced_announcement,
    get_effective_forced_announcement,
    list_forced_announcements,
    update_forced_announcement,
)
from tables import ensure_admin_tables


BEIJING_START = "2026-08-11T22:32:00"


def _insert_site(db_path, *, site_id: int, web_id: int) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO managed_sites (
                id, web_id, name, domain, lottery_type_id, enabled,
                blueprint_name, announcement, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 3, 1, ?, '', '', ?, ?)
            """,
            (
                site_id,
                web_id,
                f"site-{site_id}",
                f"site-{site_id}.example.com",
                f"site-{site_id}",
                "2026-08-11T00:00:00+00:00",
                "2026-08-11T00:00:00+00:00",
            ),
        )


@pytest.fixture
def announcement_db(tmp_path):
    db_path = tmp_path / "forced-announcements.sqlite3"
    ensure_admin_tables(db_path)
    _insert_site(db_path, site_id=901, web_id=1901)
    _insert_site(db_path, site_id=902, web_id=1902)
    return db_path


def _payload(**overrides):
    payload = {
        "title": "开奖公告",
        "html": "<p>请核对最新开奖结果</p>",
        "scope": "all_sites",
        "site_ids": [],
        "starts_at": BEIJING_START,
        "ends_at": "2026-08-11T23:00:00",
        "enabled": True,
    }
    payload.update(overrides)
    return payload


def test_effective_announcement_uses_beijing_start_inclusive_end_exclusive(
    announcement_db,
):
    created = create_forced_announcement(announcement_db, _payload())

    assert created["starts_at"] == "2026-08-11T22:32:00+08:00"
    assert created["ends_at"] == "2026-08-11T23:00:00+08:00"
    assert get_effective_forced_announcement(
        announcement_db,
        site_id=901,
        now=datetime(2026, 8, 11, 14, 31, 59, tzinfo=timezone.utc),
    ) is None
    assert get_effective_forced_announcement(
        announcement_db,
        site_id=901,
        now=datetime(2026, 8, 11, 14, 32, tzinfo=timezone.utc),
    )["id"] == created["id"]
    assert get_effective_forced_announcement(
        announcement_db,
        site_id=901,
        now=datetime(2026, 8, 11, 15, 0, tzinfo=timezone.utc),
    ) is None


def test_selected_scope_only_applies_to_selected_sites(announcement_db):
    created = create_forced_announcement(
        announcement_db,
        _payload(scope="selected_sites", site_ids=[901]),
    )
    now = datetime(2026, 8, 11, 14, 40, tzinfo=timezone.utc)

    assert get_effective_forced_announcement(
        announcement_db, site_id=901, now=now
    )["id"] == created["id"]
    assert get_effective_forced_announcement(
        announcement_db, site_id=902, now=now
    ) is None


def test_overlap_is_rejected_per_site_but_adjacent_period_is_allowed(announcement_db):
    create_forced_announcement(
        announcement_db,
        _payload(scope="selected_sites", site_ids=[901]),
    )

    with pytest.raises(ConflictError, match="901"):
        create_forced_announcement(
            announcement_db,
            _payload(
                title="重叠公告",
                starts_at="2026-08-11T22:59:59",
                ends_at="2026-08-12T00:00:00",
            ),
        )

    adjacent = create_forced_announcement(
        announcement_db,
        _payload(
            title="后续公告",
            scope="selected_sites",
            site_ids=[901],
            starts_at="2026-08-11T23:00:00",
            ends_at=None,
        ),
    )
    assert adjacent["title"] == "后续公告"


def test_update_rolls_version_and_sanitizes_controlled_html(announcement_db):
    created = create_forced_announcement(
        announcement_db,
        _payload(
            html=(
                '<p style="color:red" onclick="bad()">请<strong>确认</strong>'
                '<script>alert(1)</script><img src="x">'
                '<a href="javascript:bad()" target="_blank">危险链接</a>'
                '<a href="/notice?id=1">站内说明</a></p>'
            ),
        ),
    )

    assert created["html"] == (
        "<p>请<strong>确认</strong>"
        "<a>危险链接</a><a href=\"/notice?id=1\">站内说明</a></p>"
    )
    assert set(created) >= {"id", "version", "site_ids"}

    updated = update_forced_announcement(
        announcement_db,
        created["id"],
        {**_payload(title="更新公告"), "enabled": False},
    )

    assert updated["title"] == "更新公告"
    assert updated["version"] != created["version"]


def test_public_projection_is_minimal_and_admin_list_supports_delete(announcement_db):
    created = create_forced_announcement(
        announcement_db,
        _payload(scope="selected_sites", site_ids=[901]),
    )
    effective = get_effective_forced_announcement(
        announcement_db,
        site_id=901,
        now=datetime(2026, 8, 11, 14, 40, tzinfo=timezone.utc),
    )

    assert set(effective or {}) == {
        "id",
        "version",
        "title",
        "html",
        "starts_at",
        "ends_at",
    }
    assert list_forced_announcements(announcement_db)[0]["site_ids"] == [901]

    delete_forced_announcement(announcement_db, created["id"])
    assert list_forced_announcements(announcement_db) == []


def test_site_context_supports_manifest_site_key_for_local_vendor_development(
    announcement_db,
):
    site = resolve_site_context(
        announcement_db,
        query={"site_key": ["site-901"]},
    )

    assert site.site_id == 901
    assert site.web_id == 1901
