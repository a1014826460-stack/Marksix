"""Resolve the cache backend from explicit runtime configuration."""

from __future__ import annotations

import os

from cache.contracts import CacheStore
from cache.memory import MemoryCacheStore
from cache.redis_store import RedisCacheStore


DEVELOPMENT = "development"
PRODUCTION = "production"
_BACKENDS = {"memory", "redis"}


class CacheRuntimeError(RuntimeError):
    """The selected cache backend is unsafe for the current process profile."""


def create_cache_store(
    *,
    runtime_environment: str | None = None,
    cache_backend: str | None = None,
    redis_url: str | None = None,
) -> CacheStore:
    """Build the only approved runtime cache adapter without connecting to Redis.

    HTTP server wiring is deferred to the public-read task; that integration must
    call this factory rather than instantiate an adapter directly so production
    cannot silently fall back to in-process memory.
    """
    environment = (runtime_environment or os.getenv("LIUHECAI_RUNTIME_ENV", "")).strip().lower()
    if environment not in {DEVELOPMENT, PRODUCTION}:
        raise CacheRuntimeError("LIUHECAI_RUNTIME_ENV must be development or production.")

    backend = (cache_backend or os.getenv("CACHE_BACKEND", "")).strip().lower()
    if not backend:
        backend = "memory" if environment == DEVELOPMENT else "redis"
    if backend not in _BACKENDS:
        raise CacheRuntimeError("CACHE_BACKEND must be memory or redis.")
    if environment == PRODUCTION and backend != "redis":
        raise CacheRuntimeError("production runtime requires CACHE_BACKEND=redis.")
    if backend == "memory":
        return MemoryCacheStore()

    target = (redis_url if redis_url is not None else os.getenv("REDIS_URL", "")).strip()
    if not target:
        raise CacheRuntimeError("REDIS_URL is required when CACHE_BACKEND=redis.")
    try:
        return RedisCacheStore(target)
    except ValueError as exc:
        raise CacheRuntimeError(str(exc)) from exc
