from __future__ import annotations

from db import connect
from domains.sites import service
from tables import ensure_admin_tables


def _insert_site(
    db_path,
    *,
    site_id: int,
    web_id: int,
    enabled: int,
    announcement: str,
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO managed_sites (
                id, web_id, name, domain, lottery_type_id, enabled,
                blueprint_name, announcement, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                site_id,
                web_id,
                f"site-{site_id}",
                f"site-{site_id}.example.com",
                3,
                enabled,
                "default",
                announcement,
                "",
                "2026-06-27T00:00:00+00:00",
                "2026-06-27T00:00:00+00:00",
            ),
        )


def test_get_public_notice_returns_enabled_site_announcement_by_web_id(tmp_path):
    db_path = tmp_path / "site_notice.sqlite3"
    ensure_admin_tables(db_path)
    _insert_site(db_path, site_id=66, web_id=660, enabled=1, announcement="hello notice")

    assert service.get_public_notice(db_path, 660) == {
        "code": 600,
        "data": {"content": "hello notice"},
    }


def test_get_public_notice_preserves_legacy_id_lookup(tmp_path):
    db_path = tmp_path / "site_notice_id.sqlite3"
    ensure_admin_tables(db_path)
    _insert_site(db_path, site_id=67, web_id=670, enabled=1, announcement="legacy id notice")

    assert service.get_public_notice(db_path, 67) == {
        "code": 600,
        "data": {"content": "legacy id notice"},
    }


def test_get_public_notice_returns_empty_payload_when_missing_or_disabled(tmp_path):
    db_path = tmp_path / "site_notice_empty.sqlite3"
    ensure_admin_tables(db_path)
    _insert_site(db_path, site_id=68, web_id=680, enabled=0, announcement="hidden notice")

    assert service.get_public_notice(db_path, 680) == {
        "code": 200,
        "data": {"content": ""},
    }
    assert service.get_public_notice(db_path, None) == {
        "code": 200,
        "data": {"content": ""},
    }
