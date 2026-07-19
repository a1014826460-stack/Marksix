"""Recursive data redaction for values that must not persist in logs or APIs."""

from __future__ import annotations

import re
from typing import Any


REDACTED_VALUE = "***REDACTED***"

_SENSITIVE_KEY_PARTS = (
    "authorization",
    "captcha",
    "credential",
    "database_url",
    "dsn",
    "password",
    "res_code",
    "secret",
    "token",
)

_SENSITIVE_EXACT_KEYS = {
    "numbers",
}

_POSTGRES_DSN_PASSWORD_PATTERN = re.compile(r"(?i)(?:postgres(?:ql)?://[^\s:@/]+:)([^\s@/]+)(@)")
_SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(authorization|captcha|credential|password|res_code|secret|token|numbers)\s*[=:]\s*([^\s;]+)"
)


def is_sensitive_key(key: object) -> bool:
    normalized = str(key or "").strip().lower().replace("-", "_")
    return normalized in _SENSITIVE_EXACT_KEYS or any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def redact_text(value: object) -> str:
    """Mask credentials and future-draw fields embedded in log/error text."""
    text = str(value or "")
    text = _POSTGRES_DSN_PASSWORD_PATTERN.sub(
        lambda match: match.group(0).replace(match.group(1), REDACTED_VALUE),
        text,
    )
    text = _SENSITIVE_ASSIGNMENT_PATTERN.sub(
        lambda match: match.group(1) + "=" + REDACTED_VALUE,
        text,
    )
    return text


def redact_value(value: Any) -> Any:
    """Return a deep copy with sensitive mapping values replaced by a fixed marker."""
    if isinstance(value, dict):
        return {
            str(key): REDACTED_VALUE if is_sensitive_key(key) else redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_value(item) for item in value]
    if isinstance(value, set):
        return [redact_value(item) for item in sorted(value, key=str)]
    if isinstance(value, str):
        return redact_text(value)
    return value
