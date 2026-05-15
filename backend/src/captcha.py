"""图形验证码生成与校验。

纯标准库实现，不依赖 PIL/Pillow。生成 SVG 格式的 4 位数字字母验证码，
返回 Base64 编码的 data URI 可直接嵌入 <img> 标签。
"""

from __future__ import annotations

import base64
import random
import secrets
import string
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from db import connect

# 去除易混淆字符：0/O、1/I/L、2/Z
_CAPTCHA_CHARS = "3456789ABCDEFGHJKMNPQRSTUVWXY"
_CAPTCHA_LENGTH = 4
_CAPTCHA_TTL_MINUTES = 5


def _random_color() -> str:
    r = random.randint(40, 180)
    g = random.randint(40, 180)
    b = random.randint(40, 180)
    return f"rgb({r},{g},{b})"


def generate_captcha_svg(code: str) -> str:
    """生成包含验证码文本的 SVG 字符串，含噪点和干扰线。

    每个字符随机旋转 ±25°，位置略有偏移，增加 OCR 难度。
    """
    width = 140
    height = 52
    chars = list(code)
    char_width = width // (len(chars) + 1)

    elements: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="#f8f9fa" rx="4"/>',
    ]

    # 背景噪点
    for _ in range(30):
        cx = random.randint(0, width)
        cy = random.randint(0, height)
        r = random.randint(1, 2)
        opacity = random.uniform(0.05, 0.2)
        elements.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#000" opacity="{opacity:.2f}"/>'
        )

    # 干扰线
    for _ in range(3):
        x1 = random.randint(0, width // 3)
        y1 = random.randint(0, height)
        x2 = random.randint(width * 2 // 3, width)
        y2 = random.randint(0, height)
        color = _random_color()
        elements.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{color}" stroke-width="{random.uniform(0.5, 1.5):.1f}" opacity="0.5"/>'
        )

    # 字符
    for i, ch in enumerate(chars):
        x = char_width * (i + 1) - 8
        y = height // 2 + 8
        angle = random.randint(-25, 25)
        offset_y = random.randint(-5, 5)
        color = _random_color()
        font_size = random.randint(22, 28)
        elements.append(
            f'<text x="{x}" y="{y + offset_y}" '
            f'transform="rotate({angle}, {x}, {y + offset_y})" '
            f'font-size="{font_size}" font-family="Arial, sans-serif" '
            f'font-weight="bold" fill="{color}" '
            f'text-anchor="middle">{ch}</text>'
        )

    elements.append("</svg>")
    return "\n".join(elements)


def generate_captcha() -> tuple[str, str]:
    """生成验证码，返回 (code, base64_data_uri)。"""
    code = "".join(secrets.choice(_CAPTCHA_CHARS) for _ in range(_CAPTCHA_LENGTH))
    svg = generate_captcha_svg(code)
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return code, f"data:image/svg+xml;base64,{b64}"


def _ensure_tables(conn: Any) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_login_captcha (
            id SERIAL PRIMARY KEY,
            fingerprint TEXT NOT NULL,
            code TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (now() AT TIME ZONE 'UTC')
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_admin_login_captcha_fingerprint
        ON admin_login_captcha (fingerprint, expires_at)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_login_attempts (
            fingerprint TEXT PRIMARY KEY,
            attempt_count INTEGER NOT NULL DEFAULT 1,
            first_attempt_at TEXT NOT NULL,
            last_attempt_at TEXT NOT NULL,
            locked_until TEXT
        )
        """
    )


def store_captcha(db_path: str | Path, fingerprint: str, code: str) -> None:
    """存储验证码，关联到设备指纹。"""
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(minutes=_CAPTCHA_TTL_MINUTES)).isoformat()
    with connect(db_path) as conn:
        _ensure_tables(conn)
        # 清理同指纹旧验证码
        conn.execute(
            "DELETE FROM admin_login_captcha WHERE fingerprint = %s",
            (fingerprint,),
        )
        conn.execute(
            """INSERT INTO admin_login_captcha (fingerprint, code, expires_at, created_at)
               VALUES (%s, %s, %s, %s)""",
            (fingerprint, code, expires_at, now.isoformat()),
        )


def verify_captcha(db_path: str | Path, fingerprint: str, code: str) -> bool:
    """验证验证码是否正确且未过期。验证后删除已使用的验证码。"""
    now = datetime.now(timezone.utc).isoformat()
    with connect(db_path) as conn:
        _ensure_tables(conn)
        row = conn.execute(
            """SELECT code, expires_at FROM admin_login_captcha
               WHERE fingerprint = %s AND expires_at > %s
               ORDER BY id DESC LIMIT 1""",
            (fingerprint, now),
        ).fetchone()
        if not row:
            return False
        stored_code = str(row["code"] or "").strip().upper()
        # 验证成功后删除，防止重用
        conn.execute(
            "DELETE FROM admin_login_captcha WHERE fingerprint = %s",
            (fingerprint,),
        )
        return stored_code == code.strip().upper()


# ── 登录锁定 ──

_MAX_ATTEMPTS = 5
_ATTEMPT_WINDOW_MINUTES = 5
_LOCKOUT_MINUTES = 15


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_login_locked(db_path: str | Path, fingerprint: str) -> tuple[bool, str]:
    """检查设备是否被锁定。

    Returns:
        (is_locked, reason_message)
    """
    now = datetime.now(timezone.utc)
    window_start = (now - timedelta(minutes=_ATTEMPT_WINDOW_MINUTES)).isoformat()
    with connect(db_path) as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT * FROM admin_login_attempts WHERE fingerprint = %s",
            (fingerprint,),
        ).fetchone()
        if not row:
            return False, ""

        # 如果锁定已过期，清除记录
        locked_until = str(row["locked_until"] or "").strip()
        if locked_until and locked_until > now.isoformat():
            minutes_left = max(
                1,
                int(
                    (
                        datetime.fromisoformat(locked_until.replace("Z", "+00:00"))
                        - now
                    ).total_seconds()
                    / 60
                ),
            )
            return True, f"因多次尝试失败，该设备已被临时锁定，请 {minutes_left} 分钟后再试"

        # 检查窗口期内的失败次数
        first_attempt = str(row["first_attempt_at"] or "").strip()
        if first_attempt < window_start:
            # 窗口已过期，重置计数
            conn.execute(
                "DELETE FROM admin_login_attempts WHERE fingerprint = %s",
                (fingerprint,),
            )
            return False, ""

        if int(row["attempt_count"] or 0) >= _MAX_ATTEMPTS:
            # 锁定
            lock_until = (now + timedelta(minutes=_LOCKOUT_MINUTES)).isoformat()
            conn.execute(
                "UPDATE admin_login_attempts SET locked_until = %s, last_attempt_at = %s WHERE fingerprint = %s",
                (lock_until, _now_iso(), fingerprint),
            )
            return True, f"因多次尝试失败，该设备已被临时锁定，请 {_LOCKOUT_MINUTES} 分钟后再试"

    return False, ""


def record_login_failure(db_path: str | Path, fingerprint: str) -> dict[str, Any]:
    """记录一次登录失败，返回锁定状态信息。"""
    now_iso = _now_iso()
    with connect(db_path) as conn:
        _ensure_tables(conn)
        existing = conn.execute(
            "SELECT * FROM admin_login_attempts WHERE fingerprint = %s",
            (fingerprint,),
        ).fetchone()

        if existing:
            new_count = int(existing["attempt_count"] or 0) + 1
            locked_until = None
            if new_count >= _MAX_ATTEMPTS:
                locked_until = (
                    datetime.now(timezone.utc) + timedelta(minutes=_LOCKOUT_MINUTES)
                ).isoformat()
            conn.execute(
                """UPDATE admin_login_attempts
                   SET attempt_count = %s, last_attempt_at = %s, locked_until = %s
                   WHERE fingerprint = %s""",
                (new_count, now_iso, locked_until, fingerprint),
            )
            return {
                "attempt_count": new_count,
                "max_attempts": _MAX_ATTEMPTS,
                "locked": bool(locked_until),
                "locked_minutes": _LOCKOUT_MINUTES if locked_until else 0,
            }
        else:
            conn.execute(
                """INSERT INTO admin_login_attempts
                   (fingerprint, attempt_count, first_attempt_at, last_attempt_at)
                   VALUES (%s, 1, %s, %s)""",
                (fingerprint, now_iso, now_iso),
            )
            return {
                "attempt_count": 1,
                "max_attempts": _MAX_ATTEMPTS,
                "locked": False,
                "locked_minutes": 0,
            }


def reset_login_attempts(db_path: str | Path, fingerprint: str) -> None:
    """登录成功后清除失败记录。"""
    with connect(db_path) as conn:
        _ensure_tables(conn)
        conn.execute(
            "DELETE FROM admin_login_attempts WHERE fingerprint = %s",
            (fingerprint,),
        )
        conn.execute(
            "DELETE FROM admin_login_captcha WHERE fingerprint = %s",
            (fingerprint,),
        )
