from __future__ import annotations

import pytest

from app_http.auth import require_admin
from app_http.router import Router
from core.errors import ForbiddenError
from domains.users import service as users_service
from routes import (
    admin_alert_routes,
    admin_config_routes,
    admin_crawler_routes,
    admin_draw_routes,
    admin_log_routes,
    admin_user_routes,
)
from tables import ensure_admin_tables
from tests.helpers.api_contract import make_ctx


def test_user_service_rejects_unknown_role(tmp_path):
    db_path = str(tmp_path / "rbac-roles.sqlite3")
    ensure_admin_tables(db_path)

    with pytest.raises(ValueError, match="角色不受支持"):
        users_service.save_user(
            db_path,
            {"username": "unknown", "role": "unrecognized_role", "password": "password"},
        )


def test_user_service_preserves_an_active_super_admin(tmp_path):
    db_path = str(tmp_path / "rbac-super-admin.sqlite3")
    ensure_admin_tables(db_path)
    from db import connect

    with connect(db_path) as conn:
        conn.execute("UPDATE admin_users SET status = 0")
    only_super_admin = users_service.save_user(
        db_path,
        {"username": "root", "role": "super_admin", "status": True, "password": "password"},
    )

    with pytest.raises(ValueError, match="超级管理员"):
        users_service.save_user(
            db_path,
            {"username": "root", "role": "admin", "status": True},
            user_id=only_super_admin["id"],
        )

    with pytest.raises(ValueError, match="超级管理员"):
        users_service.delete_user(db_path, only_super_admin["id"])


def test_admin_guard_rejects_non_admin_authenticated_user():
    ctx = make_ctx("/api/admin/users")
    ctx.state["current_user"] = {"id": 2, "role": "operator"}

    with pytest.raises(ForbiddenError, match="管理员权限"):
        require_admin(ctx)


def test_user_management_routes_reject_an_admin_who_is_not_super_admin():
    router = Router()
    admin_user_routes.register(router)
    ctx = make_ctx("/api/admin/users")
    ctx.state["current_user"] = {"id": 2, "role": "admin"}

    router.dispatch(ctx)

    assert ctx.handler.response_status == 403


def test_config_routes_reject_an_admin_who_is_not_super_admin():
    router = Router()
    admin_config_routes.register(router)
    ctx = make_ctx("/api/admin/system-config")
    ctx.state["current_user"] = {"id": 2, "role": "admin"}

    router.dispatch(ctx)

    assert ctx.handler.response_status == 403


@pytest.mark.parametrize(
    ("register", "path", "method"),
    [
        (admin_crawler_routes.register, "/api/admin/crawler/run-all", "POST"),
        (admin_draw_routes.register, "/api/admin/draws", "POST"),
        (admin_log_routes.register, "/api/admin/logs/export", "GET"),
        (admin_alert_routes.register, "/api/admin/alert/test-email", "POST"),
    ],
)
def test_high_risk_admin_routes_reject_non_admin_before_handler(register, path, method):
    router = Router()
    register(router)
    ctx = make_ctx(path, method=method)
    ctx.state["current_user"] = {"id": 2, "role": "viewer"}

    router.dispatch(ctx)

    assert ctx.handler.response_status == 403


def test_site_permissions_allow_only_granted_site_for_operator(tmp_path):
    from db import connect
    from domains.sites.permissions import can_access_site, can_generate_predictions

    db_path = str(tmp_path / "rbac-site-permissions.sqlite3")
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        user_id = int(
            conn.execute(
                """
                INSERT INTO admin_users (username, display_name, password_hash, role, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                ("operator", "Operator", "hash", "operator", 1, "2026-07-19", "2026-07-19"),
            ).fetchone()["id"]
        )
        conn.execute(
            """
            INSERT INTO managed_sites (web_id, name, domain, lottery_type_id, enabled, created_at, updated_at)
            VALUES (41, 'site-41', '', NULL, 1, '2026-07-19', '2026-07-19')
            """
        )
        site_id = int(conn.execute("SELECT id FROM managed_sites WHERE web_id = 41").fetchone()["id"])
        conn.execute(
            "INSERT INTO site_permissions (user_id, site_id, can_view, can_manage, can_generate, created_at, updated_at) VALUES (?, ?, 1, 0, 1, ?, ?)",
            (user_id, site_id, "2026-07-19", "2026-07-19"),
        )

    user = {"id": user_id, "role": "operator"}
    assert can_access_site(user, site_id, db_path=db_path) is True
    assert can_generate_predictions(user, site_id, db_path=db_path) is True
    assert can_access_site(user, site_id + 999, db_path=db_path) is False
    assert can_generate_predictions(user, site_id + 999, db_path=db_path) is False


def test_site_context_requires_a_site_permission_for_operator(tmp_path, monkeypatch):
    from app_http.site_context import SiteContext, require_site_access

    db_path = str(tmp_path / "rbac-site-context.sqlite3")
    ctx = make_ctx("/api/admin/sites/19")
    ctx.handler.server.db_path = db_path
    ctx.state["current_user"] = {"id": 22, "role": "operator"}
    site = SiteContext(19, 41, "site", None, 3, True)
    monkeypatch.setattr("app_http.site_context.resolve_site_context", lambda *_args, **_kwargs: site)

    with pytest.raises(ForbiddenError, match="访问该站点"):
        require_site_access(ctx, 19)
