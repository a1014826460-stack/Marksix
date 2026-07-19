from __future__ import annotations

import inspect
from unittest.mock import patch

from routes import auth_routes
from tests.helpers.api_contract import make_ctx, response_json


def test_captcha_route_contract():
    ctx = make_ctx("/api/auth/captcha", method="GET")

    with patch("routes.auth_routes.generate_captcha", return_value=("1234", "data:image/svg+xml;base64,abc")), \
         patch("routes.auth_routes.store_captcha") as store_mock:
        auth_routes.captcha(ctx)

    payload = response_json(ctx)
    assert ctx.handler.response_status == 200
    assert payload == {
        "image": "data:image/svg+xml;base64,abc",
        "expires_in_seconds": 300,
    }
    assert store_mock.called


def test_captcha_storage_does_not_run_schema_setup_per_request():
    from captcha import store_captcha

    assert "_ensure_tables" not in inspect.getsource(store_captcha)


def test_login_missing_captcha_contract():
    ctx = make_ctx("/api/auth/login", method="POST", payload={"username": "admin", "password": "secret"})

    with patch("routes.auth_routes.check_login_locked", return_value=(False, "")):
        auth_routes.login(ctx)

    payload = response_json(ctx)
    assert ctx.handler.response_status == 400
    assert payload == {"ok": False, "error": "请输入验证码"}


def test_login_invalid_captcha_contract():
    ctx = make_ctx(
        "/api/auth/login",
        method="POST",
        payload={"username": "admin", "password": "secret", "captcha": "0000"},
    )

    with patch("routes.auth_routes.check_login_locked", return_value=(False, "")), \
         patch("routes.auth_routes.verify_captcha", return_value=False), \
         patch(
             "routes.auth_routes.record_login_failure",
             return_value={
                 "attempt_count": 1,
                 "max_attempts": 5,
                 "locked": False,
                 "locked_minutes": 0,
             },
         ):
        auth_routes.login(ctx)

    payload = response_json(ctx)
    assert ctx.handler.response_status == 400
    assert payload == {"ok": False, "error": "验证码错误"}
