from __future__ import annotations

from alerts.email_service import get_recipients, send_alert_async
from runtime_config import upsert_system_config

from app_http.request_context import RequestContext
from app_http.router import Router
from app_http.auth import require_authenticated


def register(router: Router) -> None:
    router.add("GET", "/api/admin/alert/recipients", get_alert_recipients,
               guard=require_authenticated)
    router.add("PUT", "/api/admin/alert/recipients", update_alert_recipients,
               guard=require_authenticated)
    router.add("POST", "/api/admin/alert/test-email", test_alert_email,
               guard=require_authenticated)


def get_alert_recipients(ctx: RequestContext) -> None:
    recipients = get_recipients(ctx.db_path)
    ctx.send_json({
        "ok": True,
        "data": {
            "recipients": recipients,
        },
    })


def update_alert_recipients(ctx: RequestContext) -> None:
    body = ctx.read_json()
    recipients = body.get("recipients") or []

    if not isinstance(recipients, list) or not recipients:
        ctx.send_json({"ok": False, "error": "recipients 必须为非空字符串数组"}, 400)
        return

    valid: list[str] = []
    for r in recipients:
        email = str(r).strip()
        if "@" not in email or "." not in email:
            ctx.send_json({"ok": False, "error": f"无效邮箱地址: {r}"}, 400)
            return
        valid.append(email)

    upsert_system_config(
        ctx.db_path,
        key="alert.email_recipients",
        value=valid,
        value_type="json",
        changed_by="admin",
        change_reason="后台更新报警收件人列表",
    )

    ctx.send_json({
        "ok": True,
        "data": {
            "recipients": valid,
        },
    })


def test_alert_email(ctx: RequestContext) -> None:
    send_alert_async(
        ctx.db_path,
        subject="[六合彩] 测试报警邮件",
        body_html="""
        <h2>测试报警邮件</h2>
        <p>如果您收到此邮件，说明邮件报警系统配置正确。</p>
        <p>此邮件由管理后台手动触发，用于验证 SMTP 配置和收件人地址。</p>
        """,
    )
    ctx.send_json({
        "ok": True,
        "message": "测试邮件已发送（异步），请稍后检查收件箱",
    })
