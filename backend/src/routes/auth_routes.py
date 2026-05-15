from __future__ import annotations

from http import HTTPStatus

from auth import login_user, logout_user
from app_http.auth import require_authenticated
from app_http.request_context import RequestContext
from app_http.router import Router
from captcha import (
    check_login_locked,
    generate_captcha,
    record_login_failure,
    reset_login_attempts,
    store_captcha,
    verify_captcha,
)


def register(router: Router) -> None:
    router.add("GET", "/api/auth/captcha", captcha)
    router.add("POST", "/api/auth/login", login)
    router.add("GET", "/api/auth/me", me)
    router.add("POST", "/api/auth/logout", logout)


def _device_fingerprint(ctx: RequestContext) -> str:
    """从请求中提取设备指纹：优先使用前端传入的指纹，回退到 IP + User-Agent。"""
    fp = (ctx.headers.get("X-Device-Fingerprint") or "").strip()
    if fp:
        return fp
    ip = (getattr(ctx.handler, "client_address", ("unknown",))[0] or "unknown").strip()
    ua = (ctx.headers.get("User-Agent") or "").strip()
    return f"{ip}|{ua}"[:256]


def captcha(ctx: RequestContext) -> None:
    """生成图形验证码，返回 Base64 图片和有效期。"""
    fingerprint = _device_fingerprint(ctx)
    code, image_uri = generate_captcha()
    store_captcha(ctx.db_path, fingerprint, code)
    ctx.send_json({
        "image": image_uri,
        "expires_in_seconds": 300,
    })


def login(ctx: RequestContext) -> None:
    body = ctx.read_json()
    fingerprint = _device_fingerprint(ctx)

    # 1. 检查设备是否被锁定
    locked, lock_reason = check_login_locked(ctx.db_path, fingerprint)
    if locked:
        ctx.send_json({"ok": False, "error": lock_reason, "locked": True},
                       HTTPStatus.TOO_MANY_REQUESTS)
        return

    # 2. 验证图形验证码
    captcha_code = str(body.get("captcha") or "").strip()
    if not captcha_code:
        ctx.send_json({"ok": False, "error": "请输入验证码"}, HTTPStatus.BAD_REQUEST)
        return
    if not verify_captcha(ctx.db_path, fingerprint, captcha_code):
        record_login_failure(ctx.db_path, fingerprint)
        ctx.send_json({"ok": False, "error": "验证码错误"}, HTTPStatus.BAD_REQUEST)
        return

    # 3. 验证用户名密码
    try:
        result = login_user(
            ctx.db_path,
            str(body.get("username") or ""),
            str(body.get("password") or ""),
        )
    except PermissionError:
        failure_info = record_login_failure(ctx.db_path, fingerprint)
        remaining = max(0, failure_info["max_attempts"] - failure_info["attempt_count"])
        locked_msg = ""
        if failure_info["locked"]:
            locked_msg = f" 该设备已被锁定 {failure_info['locked_minutes']} 分钟。"
        ctx.send_json(
            {
                "ok": False,
                "error": f"用户名或密码错误。剩余尝试次数：{remaining}。" + locked_msg,
                "attempt_count": failure_info["attempt_count"],
                "max_attempts": failure_info["max_attempts"],
                "locked": failure_info["locked"],
            },
            HTTPStatus.UNAUTHORIZED,
        )
        return

    # 登录成功，清除设备锁定记录
    reset_login_attempts(ctx.db_path, fingerprint)
    ctx.send_json(result)


def me(ctx: RequestContext) -> None:
    user = require_authenticated(ctx)
    ctx.send_json({"user": user})


def logout(ctx: RequestContext) -> None:
    logout_user(ctx.db_path, ctx.bearer_token())
    ctx.send_json({"ok": True})
