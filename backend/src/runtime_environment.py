"""Runtime-profile guards for database service processes.

Development services run on the Windows host. Production services run inside the
Docker Compose network. Keeping their database endpoints disjoint prevents an
operator from accidentally crossing the two environments.
"""

from __future__ import annotations

import os
from urllib.parse import urlsplit


DEVELOPMENT = "development"
PRODUCTION = "production"
_DEVELOPMENT_HOSTS = {"127.0.0.1", "localhost", "::1"}
_PRODUCTION_HOST = "pgbouncer"
_DATABASE_MODES = {"compose", "managed"}


class RuntimeEnvironmentError(RuntimeError):
    """The process profile and PostgreSQL endpoint are incompatible."""


def _runtime_environment(value: str | None) -> str:
    profile = (value if value is not None else os.getenv("LIUHECAI_RUNTIME_ENV", "")).strip().lower()
    if profile not in {DEVELOPMENT, PRODUCTION}:
        raise RuntimeEnvironmentError(
            "LIUHECAI_RUNTIME_ENV must be explicitly set to development or production."
        )
    return profile


def _endpoint(target: str) -> tuple[str, int]:
    parsed = urlsplit(str(target or ""))
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
        raise RuntimeEnvironmentError("DATABASE_URL must be a PostgreSQL DSN with a host.")
    try:
        port = parsed.port or 5432
    except ValueError as exc:
        raise RuntimeEnvironmentError("DATABASE_URL contains an invalid port.") from exc
    return parsed.hostname.lower(), port


def validate_runtime_database_target(
    target: str,
    *,
    runtime_environment: str | None = None,
    database_mode: str | None = None,
) -> None:
    """Reject database DSNs that do not belong to the declared runtime profile."""
    profile = _runtime_environment(runtime_environment)
    host, port = _endpoint(target)

    if profile == DEVELOPMENT:
        if host not in _DEVELOPMENT_HOSTS or port != 5432:
            raise RuntimeEnvironmentError(
                "development runtime only accepts Windows native PostgreSQL at "
                "127.0.0.1/localhost:5432."
            )
        return

    mode = (database_mode or os.getenv("LIUHECAI_DATABASE_MODE", "compose")).strip().lower()
    if mode not in _DATABASE_MODES:
        raise RuntimeEnvironmentError(
            "LIUHECAI_DATABASE_MODE must be explicitly set to compose or managed."
        )
    if mode == "managed":
        if host in _DEVELOPMENT_HOSTS:
            raise RuntimeEnvironmentError("managed production database cannot use a loopback host.")
        return

    if host != _PRODUCTION_HOST or port != 6432:
        raise RuntimeEnvironmentError(
            "production runtime only accepts Docker Compose PgBouncer at pgbouncer:6432."
        )
