from __future__ import annotations

from unittest.mock import patch

from app_http.router import Router
from app_http.auth import require_super_admin
from routes import admin_forced_announcement_routes, public_routes
from tests.helpers.api_contract import make_ctx, response_json


PUBLIC_ANNOUNCEMENT = {
    "id": 8,
    "version": "version-8",
    "title": "开奖公告",
    "html": "<p>请确认</p>",
    "starts_at": "2026-08-11T22:32:00+08:00",
    "ends_at": None,
}


def test_public_forced_announcement_resolves_site_and_reads_replica():
    ctx = make_ctx("/api/public/forced-announcement?site_id=901")
    ctx.handler.server.read_db_path = "postgresql://readonly/lottery"
    site = type("Site", (), {"site_id": 901})()

    with patch(
        "routes.public_routes.resolve_site_context", return_value=site
    ) as resolve_site, patch(
        "routes.public_routes.get_effective_forced_announcement",
        return_value=PUBLIC_ANNOUNCEMENT,
    ) as get_effective:
        public_routes.forced_announcement(ctx)

    resolve_site.assert_called_once_with(
        ctx.write_db_path,
        query=ctx.query,
        host="",
    )
    get_effective.assert_called_once_with(ctx.read_db_path, site_id=901)
    assert response_json(ctx) == PUBLIC_ANNOUNCEMENT


def test_public_forced_announcement_returns_json_null_when_inactive():
    ctx = make_ctx("/api/public/forced-announcement?site_id=901")
    site = type("Site", (), {"site_id": 901})()
    with patch("routes.public_routes.resolve_site_context", return_value=site), patch(
        "routes.public_routes.get_effective_forced_announcement", return_value=None
    ):
        public_routes.forced_announcement(ctx)

    assert response_json(ctx) is None


def test_admin_forced_announcement_crud_contracts():
    list_ctx = make_ctx("/api/admin/forced-announcements")
    with patch(
        "routes.admin_forced_announcement_routes.list_forced_announcements",
        return_value=[PUBLIC_ANNOUNCEMENT],
    ):
        admin_forced_announcement_routes.list_announcements(list_ctx)
    assert response_json(list_ctx) == {"announcements": [PUBLIC_ANNOUNCEMENT]}

    create_ctx = make_ctx(
        "/api/admin/forced-announcements", "POST", {"title": "公告"}
    )
    with patch(
        "routes.admin_forced_announcement_routes.create_forced_announcement",
        return_value=PUBLIC_ANNOUNCEMENT,
    ) as create:
        admin_forced_announcement_routes.create_announcement(create_ctx)
    create.assert_called_once_with(create_ctx.db_path, {"title": "公告"})
    assert create_ctx.handler.response_status == 201
    assert response_json(create_ctx) == {"announcement": PUBLIC_ANNOUNCEMENT}

    update_ctx = make_ctx(
        "/api/admin/forced-announcements/8", "PUT", {"title": "更新"}
    )
    with patch(
        "routes.admin_forced_announcement_routes.update_forced_announcement",
        return_value=PUBLIC_ANNOUNCEMENT,
    ) as update:
        admin_forced_announcement_routes.announcement_detail(update_ctx)
    update.assert_called_once_with(update_ctx.db_path, 8, {"title": "更新"})
    assert response_json(update_ctx) == {"announcement": PUBLIC_ANNOUNCEMENT}

    delete_ctx = make_ctx("/api/admin/forced-announcements/8", "DELETE")
    with patch(
        "routes.admin_forced_announcement_routes.delete_forced_announcement"
    ) as delete:
        admin_forced_announcement_routes.announcement_detail(delete_ctx)
    delete.assert_called_once_with(delete_ctx.db_path, 8)
    assert response_json(delete_ctx) == {"ok": True}


def test_admin_forced_announcement_routes_require_super_admin():
    router = Router()
    admin_forced_announcement_routes.register(router)

    matching = [
        route
        for route in router._routes
        if route.matcher(make_ctx("/api/admin/forced-announcements"))
    ]
    assert matching
    assert all(route.guard is require_super_admin for route in matching)

