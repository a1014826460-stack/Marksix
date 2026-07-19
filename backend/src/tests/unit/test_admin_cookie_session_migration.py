from __future__ import annotations

from pathlib import Path


_ROOT = Path(__file__).resolve().parents[4]


def test_next_admin_proxy_forwards_cookie_and_set_cookie_headers():
    source = (_ROOT / "backend" / "app" / "api" / "python" / "[...path]" / "route.ts").read_text(encoding="utf-8")

    assert 'request.headers.get("cookie")' in source
    assert 'headers.set("cookie", cookie)' in source
    assert 'request.headers.get("x-forwarded-proto")' in source
    assert 'headers.set("x-forwarded-proto", forwardedProto)' in source
    assert 'response.headers.get("set-cookie")' in source
    assert 'responseHeaders.set("set-cookie", setCookie)' in source


def test_admin_ui_uses_http_only_cookie_instead_of_local_storage_tokens():
    admin_api = (_ROOT / "backend" / "lib" / "admin-api.ts").read_text(encoding="utf-8")
    login_page = (_ROOT / "backend" / "features" / "auth" / "LoginPage.tsx").read_text(encoding="utf-8")
    auth_guard = (_ROOT / "backend" / "components" / "admin" / "auth-guard.tsx").read_text(encoding="utf-8")
    admin_shell = (_ROOT / "backend" / "components" / "admin" / "admin-shell.tsx").read_text(encoding="utf-8")

    assert "liuhecai_admin_token" not in admin_api
    assert "setAdminToken" not in login_page
    assert "getAdminToken" not in auth_guard
    assert "getAdminToken" not in admin_shell
