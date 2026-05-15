"""邮件发送服务。

使用 Python 标准库 smtplib + email 发送报警邮件。
SMTP 配置从 system_config 表读取，管理员可通过后台实时修改。
"""

from __future__ import annotations

import logging
import smtplib
import socket
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from typing import Any

from runtime_config import get_config

_email_logger = logging.getLogger("alert.email")


def _cfg(db_path: str | Path, key: str, fallback: Any) -> Any:
    try:
        return get_config(db_path, key, fallback)
    except Exception:
        return fallback


def _get_server_identity() -> str:
    """获取服务器标识信息（主机名 + IP），用于报警邮件中定位问题服务器。"""
    hostname = "unknown"
    try:
        hostname = socket.gethostname()
    except Exception:
        pass
    ip = "unknown"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1.0)
        s.connect(("10.254.254.254", 1))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        try:
            ip = socket.gethostbyname(hostname)
        except Exception:
            pass
    return f"{hostname} ({ip})"


def _load_smtp_config(db_path: str | Path) -> dict[str, Any]:
    return {
        "host": str(_cfg(db_path, "alert.smtp_host", "smtp.qq.com")),
        "port": int(_cfg(db_path, "alert.smtp_port", 587)),
        "username": str(_cfg(db_path, "alert.smtp_username", "")),
        "password": str(_cfg(db_path, "alert.smtp_password", "")),
        "from_name": str(_cfg(db_path, "alert.smtp_from_name", "Liuhecai 报警系统")),
    }


def get_recipients(db_path: str | Path) -> list[str]:
    admin_email_raw = _cfg(db_path, "admin_email", "")
    admin_email = (
        str(admin_email_raw).strip()
        if isinstance(admin_email_raw, str)
        else ""
    )
    if admin_email and "@" in admin_email:
        return [admin_email]
    raw = _cfg(db_path, "alert.email_recipients", ["1014826460@qq.com"])
    if isinstance(raw, list):
        return [str(r).strip() for r in raw if str(r).strip()]
    if isinstance(raw, str):
        return [r.strip() for r in raw.split(",") if r.strip()]
    return ["1014826460@qq.com"]


def send_alert_email(
    db_path: str | Path,
    subject: str,
    body_html: str,
) -> bool:
    """发送报警邮件（同步，在后台线程中调用以免阻塞主流程）。

    :param db_path: 数据库路径，用于读取 SMTP 配置和收件人
    :param subject: 邮件主题
    :param body_html: 邮件正文（HTML 格式）
    :return: True 表示发送成功
    """
    if not _cfg(db_path, "alert.email_enabled", True):
        _email_logger.info("Email alert disabled, skipping: %s", subject)
        return False

    smtp = _load_smtp_config(db_path)
    if not smtp["username"] or not smtp["password"]:
        _email_logger.warning(
            "SMTP 未配置用户名或密码，跳过邮件发送: %s", subject
        )
        return False

    recipients = get_recipients(db_path)
    if not recipients:
        _email_logger.warning("无收件人配置，跳过邮件发送: %s", subject)
        return False

    server_id = _get_server_identity()
    full_body = (
        body_html
        + f"<hr><p style='color:#888;font-size:12px'>服务器: {server_id}</p>"
    )
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((smtp["from_name"], smtp["username"]))
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(full_body, "html", "utf-8"))

    try:
        server = smtplib.SMTP(smtp["host"], smtp["port"], timeout=15)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp["username"], smtp["password"])
        server.sendmail(smtp["username"], recipients, msg.as_string())
        server.quit()
        _email_logger.info("Alert email sent: %s → %s", subject, recipients)
        return True
    except Exception as exc:
        _email_logger.error("Failed to send alert email '%s': %s", subject, exc)
        return False


def send_alert_async(
    db_path: str | Path,
    subject: str,
    body_html: str,
) -> None:
    """异步发送报警邮件（不阻塞调用方）。"""
    t = threading.Thread(
        target=send_alert_email,
        args=(db_path, subject, body_html),
        daemon=True,
    )
    t.start()
