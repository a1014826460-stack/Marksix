from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from db import is_postgres_target


@dataclass(frozen=True)
class DatabaseTargets:
    write: str
    read: str


def _required_postgres_target(name: str, value: str) -> str:
    target = str(value or "").strip()
    if not is_postgres_target(target):
        raise RuntimeError(f"{name} must be a PostgreSQL DSN.")
    return target


def resolve_database_targets(
    *,
    explicit_write: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> DatabaseTargets:
    env = os.environ if environ is None else environ
    write_value = (
        str(explicit_write or "").strip()
        or str(env.get("DATABASE_WRITE_URL", "")).strip()
        or str(env.get("DATABASE_URL", "")).strip()
    )
    if not write_value:
        raise RuntimeError("Set DATABASE_WRITE_URL or DATABASE_URL before starting the service.")

    write = _required_postgres_target("DATABASE_WRITE_URL or DATABASE_URL", write_value)
    read_value = str(env.get("DATABASE_READ_URL", "")).strip() or write
    read = _required_postgres_target("DATABASE_READ_URL", read_value)
    return DatabaseTargets(write=write, read=read)
